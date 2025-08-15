"""
Twitter Client

This module handles all Twitter API interactions for the kubetools bot.

Author: Ajeet Singh Raina
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import tweepy
import structlog

logger = structlog.get_logger()


class TwitterClient:
    """Twitter API client for posting tweets and managing account."""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, 
                 access_token_secret: str, bearer_token: str):
        """Initialize Twitter client with API credentials."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token
        
        # Initialize Tweepy clients
        self._init_clients()
        
        logger.info("Twitter client initialized")
    
    def _init_clients(self):
        """Initialize Tweepy API clients."""
        try:
            # OAuth 1.0a for posting tweets
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
            
            # OAuth 2.0 Bearer Token for API v2
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
            
            logger.info("Tweepy clients initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Twitter clients", error=str(e))
            raise
    
    async def post_tweet(self, content: str, media_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Post a tweet with optional media."""
        try:
            logger.info("Posting tweet", content_length=len(content))
            
            # Use API v2 to post tweet
            response = self.client.create_tweet(
                text=content,
                media_ids=media_ids
            )
            
            if response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/kubetools/status/{tweet_id}"
                
                logger.info("Tweet posted successfully", 
                           tweet_id=tweet_id, 
                           tweet_url=tweet_url)
                
                return {
                    'id': tweet_id,
                    'url': tweet_url,
                    'text': content,
                    'posted_at': datetime.utcnow().isoformat()
                }
            else:
                logger.error("Failed to post tweet - no response data")
                return None
                
        except tweepy.TooManyRequests:
            logger.warning("Rate limit hit while posting tweet")
            return None
        except tweepy.Forbidden as e:
            logger.error("Forbidden error while posting tweet", error=str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error while posting tweet", error=str(e))
            return None
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        try:
            # Get rate limit status from API v1
            rate_limit = self.api_v1.get_rate_limit_status()
            
            # Extract relevant endpoints
            relevant_endpoints = {
                'statuses_update': rate_limit['resources']['statuses']['/statuses/update'],
                'statuses_user_timeline': rate_limit['resources']['statuses']['/statuses/user_timeline'],
                'application_rate_limit': rate_limit['resources']['application']['/application/rate_limit_status']
            }
            
            logger.info("Retrieved rate limit status")
            return relevant_endpoints
            
        except Exception as e:
            logger.error("Failed to get rate limit status", error=str(e))
            return {}
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the authenticated account."""
        try:
            # Get authenticated user info
            user = self.client.get_me(
                user_fields=['public_metrics', 'created_at', 'description']
            )
            
            if user.data:
                account_info = {
                    'id': user.data.id,
                    'username': user.data.username,
                    'name': user.data.name,
                    'description': user.data.description,
                    'followers_count': user.data.public_metrics['followers_count'],
                    'following_count': user.data.public_metrics['following_count'],
                    'tweet_count': user.data.public_metrics['tweet_count'],
                    'created_at': user.data.created_at.isoformat() if user.data.created_at else None
                }
                
                logger.info("Retrieved account info", 
                           username=account_info['username'],
                           followers=account_info['followers_count'])
                
                return account_info
            else:
                logger.error("Failed to get account info - no user data")
                return None
                
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            return None
    
    async def get_recent_tweets(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent tweets from the account."""
        try:
            # Get authenticated user first
            me = self.client.get_me()
            if not me.data:
                logger.error("Could not get authenticated user")
                return []
            
            user_id = me.data.id
            
            # Get recent tweets
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=min(count, 100),  # API limit
                tweet_fields=['created_at', 'public_metrics', 'context_annotations']
            )
            
            if not tweets.data:
                logger.info("No recent tweets found")
                return []
            
            recent_tweets = []
            for tweet in tweets.data:
                tweet_data = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'url': f"https://twitter.com/kubetools/status/{tweet.id}",
                    'metrics': {
                        'retweet_count': tweet.public_metrics.get('retweet_count', 0),
                        'like_count': tweet.public_metrics.get('like_count', 0),
                        'reply_count': tweet.public_metrics.get('reply_count', 0),
                        'quote_count': tweet.public_metrics.get('quote_count', 0)
                    } if tweet.public_metrics else {}
                }
                recent_tweets.append(tweet_data)
            
            logger.info(f"Retrieved {len(recent_tweets)} recent tweets")
            return recent_tweets
            
        except Exception as e:
            logger.error("Failed to get recent tweets", error=str(e))
            return []
    
    async def search_tweets(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search for tweets with a specific query."""
        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=min(count, 100),
                tweet_fields=['created_at', 'author_id', 'public_metrics']
            )
            
            if not tweets.data:
                logger.info("No tweets found for query", query=query)
                return []
            
            found_tweets = []
            for tweet in tweets.data:
                tweet_data = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'author_id': tweet.author_id,
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'url': f"https://twitter.com/i/status/{tweet.id}",
                    'metrics': {
                        'retweet_count': tweet.public_metrics.get('retweet_count', 0),
                        'like_count': tweet.public_metrics.get('like_count', 0),
                        'reply_count': tweet.public_metrics.get('reply_count', 0),
                        'quote_count': tweet.public_metrics.get('quote_count', 0)
                    } if tweet.public_metrics else {}
                }
                found_tweets.append(tweet_data)
            
            logger.info(f"Found {len(found_tweets)} tweets for query", 
                       query=query, count=len(found_tweets))
            return found_tweets
            
        except Exception as e:
            logger.error("Failed to search tweets", query=query, error=str(e))
            return []
    
    async def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet by ID."""
        try:
            response = self.client.delete_tweet(tweet_id)
            
            if response.data and response.data['deleted']:
                logger.info("Tweet deleted successfully", tweet_id=tweet_id)
                return True
            else:
                logger.error("Failed to delete tweet", tweet_id=tweet_id)
                return False
                
        except Exception as e:
            logger.error("Error deleting tweet", tweet_id=tweet_id, error=str(e))
            return False
    
    async def upload_media(self, media_path: str) -> Optional[str]:
        """Upload media file and return media ID."""
        try:
            # Use API v1 for media upload
            media = self.api_v1.media_upload(filename=media_path)
            
            logger.info("Media uploaded successfully", 
                       media_id=media.media_id_string,
                       media_path=media_path)
            
            return media.media_id_string
            
        except Exception as e:
            logger.error("Failed to upload media", 
                        media_path=media_path, error=str(e))
            return None
    
    async def health_check(self) -> bool:
        """Perform health check on Twitter API connectivity."""
        try:
            # Try to get account info
            account_info = await self.get_account_info()
            if account_info:
                logger.info("Twitter API health check passed", 
                           username=account_info.get('username'))
                return True
            else:
                logger.error("Twitter API health check failed - no account info")
                return False
                
        except Exception as e:
            logger.error("Twitter API health check failed", error=str(e))
            return False
    
    async def get_engagement_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get engagement metrics for recent tweets."""
        try:
            recent_tweets = await self.get_recent_tweets(count=50)
            
            # Filter tweets from the specified time period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            period_tweets = [
                tweet for tweet in recent_tweets
                if tweet.get('created_at') and 
                datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')) >= cutoff_date
            ]
            
            if not period_tweets:
                return {
                    'period_days': days,
                    'tweet_count': 0,
                    'total_engagement': 0,
                    'average_engagement': 0
                }
            
            total_likes = sum(tweet['metrics'].get('like_count', 0) for tweet in period_tweets)
            total_retweets = sum(tweet['metrics'].get('retweet_count', 0) for tweet in period_tweets)
            total_replies = sum(tweet['metrics'].get('reply_count', 0) for tweet in period_tweets)
            total_quotes = sum(tweet['metrics'].get('quote_count', 0) for tweet in period_tweets)
            
            total_engagement = total_likes + total_retweets + total_replies + total_quotes
            average_engagement = total_engagement / len(period_tweets) if period_tweets else 0
            
            metrics = {
                'period_days': days,
                'tweet_count': len(period_tweets),
                'total_likes': total_likes,
                'total_retweets': total_retweets,
                'total_replies': total_replies,
                'total_quotes': total_quotes,
                'total_engagement': total_engagement,
                'average_engagement': round(average_engagement, 2)
            }
            
            logger.info("Calculated engagement metrics", **metrics)
            return metrics
            
        except Exception as e:
            logger.error("Failed to get engagement metrics", error=str(e))
            return {}
    
    async def check_for_mentions(self) -> List[Dict[str, Any]]:
        """Check for mentions of the bot account."""
        try:
            # Get authenticated user
            me = self.client.get_me()
            if not me.data:
                return []
            
            username = me.data.username
            
            # Search for mentions
            mentions = await self.search_tweets(f"@{username}", count=20)
            
            logger.info(f"Found {len(mentions)} mentions", count=len(mentions))
            return mentions
            
        except Exception as e:
            logger.error("Failed to check for mentions", error=str(e))
            return []
