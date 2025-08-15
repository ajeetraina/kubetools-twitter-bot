#!/usr/bin/env python3
"""
Kubetools Twitter Bot - Main Application

This is the main entry point for the Kubetools Twitter Bot that monitors
the kubetools repository for new Kubernetes tools and tweets about them.

Author: Ajeet Singh Raina
Version: 1.0.0
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import schedule
import structlog
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(str(Path(__file__).parent))

from database import Database
from kubetools_monitor import KubetoolsMonitor
from scheduler import TweetScheduler
from tweet_generator import TweetGenerator
from twitter_client import TwitterClient

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class KubetoolsTwitterBot:
    """Main Twitter bot class that coordinates all components."""
    
    def __init__(self):
        """Initialize the Twitter bot with all components."""
        self.config = self._load_config()
        self.database = Database()
        self.monitor = KubetoolsMonitor(
            github_token=os.getenv('GITHUB_TOKEN'),
            database=self.database
        )
        self.twitter_client = TwitterClient(
            api_key=os.getenv('TWITTER_API_KEY'),
            api_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
        )
        self.tweet_generator = TweetGenerator()
        self.scheduler = TweetScheduler(
            twitter_client=self.twitter_client,
            database=self.database,
            tweets_per_day=self.config.get('tweets_per_day', 4)
        )
        
        logger.info("Kubetools Twitter Bot initialized", 
                   tweets_per_day=self.config.get('tweets_per_day', 4))
    
    def _load_config(self) -> dict:
        """Load configuration from environment variables."""
        return {
            'tweets_per_day': int(os.getenv('TWEETS_PER_DAY', '4')),
            'timezone': os.getenv('TIMEZONE', 'UTC'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'environment': os.getenv('BOT_ENVIRONMENT', 'development'),
            'github_repo': 'collabnix/kubetools',
            'check_interval_hours': int(os.getenv('CHECK_INTERVAL_HOURS', '2')),
        }
    
    async def check_for_new_tools(self) -> None:
        """Check for new tools in the kubetools repository."""
        try:
            logger.info("Starting check for new tools")
            
            # Monitor for new tools
            new_tools = await self.monitor.check_for_new_tools()
            
            if not new_tools:
                logger.info("No new tools found")
                return
            
            logger.info(f"Found {len(new_tools)} new tools", count=len(new_tools))
            
            # Generate tweets for new tools
            for tool in new_tools:
                try:
                    tweet_content = self.tweet_generator.generate_tweet(tool)
                    
                    # Add to tweet queue
                    await self.scheduler.add_to_queue(tool, tweet_content)
                    
                    logger.info("Added tool to tweet queue", 
                               tool_name=tool.get('name', 'Unknown'))
                    
                except Exception as e:
                    logger.error("Failed to generate tweet for tool", 
                               tool_name=tool.get('name', 'Unknown'),
                               error=str(e))
            
        except Exception as e:
            logger.error("Failed to check for new tools", error=str(e))
    
    async def process_tweet_queue(self) -> None:
        """Process the tweet queue and post scheduled tweets."""
        try:
            logger.info("Processing tweet queue")
            
            # Check if it's time to post a tweet
            if await self.scheduler.should_post_tweet():
                tweet_posted = await self.scheduler.post_next_tweet()
                if tweet_posted:
                    logger.info("Successfully posted scheduled tweet")
                else:
                    logger.info("No tweets ready to post")
            else:
                logger.info("Not time to post tweet yet")
                
        except Exception as e:
            logger.error("Failed to process tweet queue", error=str(e))
    
    async def run_once(self) -> None:
        """Run a single iteration of the bot (useful for scheduled runs)."""
        logger.info("Running single bot iteration")
        
        # Check for new tools
        await self.check_for_new_tools()
        
        # Process tweet queue
        await self.process_tweet_queue()
        
        # Log statistics
        stats = await self.get_stats()
        logger.info("Bot iteration completed", **stats)
    
    async def run_continuous(self) -> None:
        """Run the bot continuously with scheduled checks."""
        logger.info("Starting continuous bot operation")
        
        # Schedule periodic checks
        schedule.every(self.config['check_interval_hours']).hours.do(
            lambda: asyncio.create_task(self.check_for_new_tools())
        )
        
        # Schedule tweet processing every 30 minutes
        schedule.every(30).minutes.do(
            lambda: asyncio.create_task(self.process_tweet_queue())
        )
        
        # Main loop
        while True:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error("Error in main loop", error=str(e))
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def get_stats(self) -> dict:
        """Get bot statistics."""
        try:
            total_tools = await self.database.get_total_tools_count()
            queued_tweets = await self.database.get_queued_tweets_count()
            posted_tweets = await self.database.get_posted_tweets_count()
            
            return {
                'total_tools_tracked': total_tools,
                'tweets_queued': queued_tweets,
                'tweets_posted': posted_tweets,
                'last_check': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Failed to get stats", error=str(e))
            return {}
    
    async def health_check(self) -> dict:
        """Perform health check of all components."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {}
        }
        
        try:
            # Check database connection
            await self.database.health_check()
            health['components']['database'] = 'healthy'
        except Exception as e:
            health['components']['database'] = f'unhealthy: {str(e)}'
            health['status'] = 'unhealthy'
        
        try:
            # Check Twitter API
            await self.twitter_client.health_check()
            health['components']['twitter'] = 'healthy'
        except Exception as e:
            health['components']['twitter'] = f'unhealthy: {str(e)}'
            health['status'] = 'unhealthy'
        
        try:
            # Check GitHub API
            await self.monitor.health_check()
            health['components']['github'] = 'healthy'
        except Exception as e:
            health['components']['github'] = f'unhealthy: {str(e)}'
            health['status'] = 'unhealthy'
        
        return health


async def main():
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kubetools Twitter Bot')
    parser.add_argument('--mode', choices=['once', 'continuous', 'health'], 
                       default='once', help='Run mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        logging.basicConfig(level=getattr(logging, log_level))
    
    # Initialize bot
    bot = KubetoolsTwitterBot()
    
    try:
        if args.mode == 'once':
            await bot.run_once()
        elif args.mode == 'continuous':
            await bot.run_continuous()
        elif args.mode == 'health':
            health = await bot.health_check()
            print(f"Health Status: {health['status']}")
            for component, status in health['components'].items():
                print(f"  {component}: {status}")
            if health['status'] != 'healthy':
                sys.exit(1)
    
    except Exception as e:
        logger.error("Fatal error in bot", error=str(e))
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
