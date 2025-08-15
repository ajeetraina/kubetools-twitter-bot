"""
Tweet Scheduler

This module handles the scheduling and timing of tweets to ensure
optimal posting frequency and timing.

Author: Ajeet Singh Raina
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import pytz
import structlog

logger = structlog.get_logger()


@dataclass
class QueuedTweet:
    """Represents a tweet in the queue."""
    id: str
    tool_data: Dict[str, Any]
    tweet_content: str
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    priority: int = 1  # 1=normal, 2=high, 3=urgent
    attempts: int = 0
    max_attempts: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'tool_data': self.tool_data,
            'tweet_content': self.tweet_content,
            'created_at': self.created_at.isoformat(),
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'priority': self.priority,
            'attempts': self.attempts,
            'max_attempts': self.max_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedTweet':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            tool_data=data['tool_data'],
            tweet_content=data['tweet_content'],
            created_at=datetime.fromisoformat(data['created_at']),
            scheduled_for=datetime.fromisoformat(data['scheduled_for']) if data.get('scheduled_for') else None,
            priority=data.get('priority', 1),
            attempts=data.get('attempts', 0),
            max_attempts=data.get('max_attempts', 3)
        )


class TweetScheduler:
    """Manages tweet scheduling and posting logic."""
    
    def __init__(self, twitter_client, database, tweets_per_day: int = 4):
        """Initialize the scheduler."""
        self.twitter_client = twitter_client
        self.database = database
        self.tweets_per_day = tweets_per_day
        self.timezone = pytz.UTC
        
        # Optimal posting hours (UTC)
        self.optimal_hours = [9, 13, 17, 21]  # 9am, 1pm, 5pm, 9pm UTC
        
        # Minimum time between tweets (hours)
        self.min_interval_hours = max(24 // tweets_per_day - 1, 2)
        
        # Queue file for persistence
        self.queue_file = Path("data/tweet_queue.json")
        self.queue_file.parent.mkdir(exist_ok=True)
        
        # Load existing queue
        self.tweet_queue: List[QueuedTweet] = self._load_queue()
        
        logger.info("Tweet scheduler initialized", 
                   tweets_per_day=tweets_per_day,
                   min_interval_hours=self.min_interval_hours)
    
    async def add_to_queue(self, tool_data: Dict[str, Any], tweet_content: str, 
                          priority: int = 1) -> str:
        """Add a tweet to the queue."""
        try:
            # Generate unique ID
            tweet_id = f"{tool_data.get('name', 'tool')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Create queued tweet
            queued_tweet = QueuedTweet(
                id=tweet_id,
                tool_data=tool_data,
                tweet_content=tweet_content,
                created_at=datetime.utcnow(),
                priority=priority
            )
            
            # Schedule the tweet
            scheduled_time = await self._calculate_next_slot()
            queued_tweet.scheduled_for = scheduled_time
            
            # Add to queue
            self.tweet_queue.append(queued_tweet)
            
            # Sort queue by priority and scheduled time
            self._sort_queue()
            
            # Save queue
            self._save_queue()
            
            # Update database
            await self.database.add_queued_tweet(queued_tweet)
            
            logger.info("Tweet added to queue", 
                       tweet_id=tweet_id,
                       tool_name=tool_data.get('name', 'Unknown'),
                       scheduled_for=scheduled_time.isoformat())
            
            return tweet_id
            
        except Exception as e:
            logger.error("Failed to add tweet to queue", error=str(e))
            raise
    
    async def should_post_tweet(self) -> bool:
        """Check if it's time to post a tweet."""
        try:
            if not self.tweet_queue:
                return False
            
            now = datetime.utcnow()
            
            # Check if we have a tweet ready to post
            next_tweet = self.tweet_queue[0]
            if next_tweet.scheduled_for and next_tweet.scheduled_for <= now:
                return True
            
            # Check if we haven't posted in a while (fallback)
            last_tweet_time = await self.database.get_last_tweet_time()
            if last_tweet_time:
                time_since_last = now - last_tweet_time
                if time_since_last.total_seconds() > (self.min_interval_hours * 3600):
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Error checking if should post tweet", error=str(e))
            return False
    
    async def post_next_tweet(self) -> bool:
        """Post the next tweet in the queue."""
        try:
            if not self.tweet_queue:
                logger.info("No tweets in queue to post")
                return False
            
            # Get next tweet
            next_tweet = self.tweet_queue[0]
            
            # Attempt to post the tweet
            logger.info("Attempting to post tweet", tweet_id=next_tweet.id)
            
            result = await self.twitter_client.post_tweet(next_tweet.tweet_content)
            
            if result:
                # Success - remove from queue and update database
                self.tweet_queue.pop(0)
                self._save_queue()
                
                await self.database.mark_tweet_posted(next_tweet.id, result)
                await self.database.update_last_tweet_time()
                
                logger.info("Tweet posted successfully", 
                           tweet_id=next_tweet.id,
                           twitter_id=result.get('id'),
                           tool_name=next_tweet.tool_data.get('name', 'Unknown'))
                
                return True
            else:
                # Failed - increment attempts
                next_tweet.attempts += 1
                
                if next_tweet.attempts >= next_tweet.max_attempts:
                    # Remove failed tweet
                    self.tweet_queue.pop(0)
                    await self.database.mark_tweet_failed(next_tweet.id)
                    
                    logger.warning("Tweet failed after max attempts", 
                                 tweet_id=next_tweet.id,
                                 attempts=next_tweet.attempts)
                else:
                    # Reschedule for later
                    next_tweet.scheduled_for = datetime.utcnow() + timedelta(hours=1)
                    self._sort_queue()
                    
                    logger.warning("Tweet attempt failed, rescheduled", 
                                 tweet_id=next_tweet.id,
                                 attempts=next_tweet.attempts,
                                 rescheduled_for=next_tweet.scheduled_for.isoformat())
                
                self._save_queue()
                return False
                
        except Exception as e:
            logger.error("Error posting tweet", error=str(e))
            return False
    
    async def _calculate_next_slot(self) -> datetime:
        """Calculate the next available time slot for posting."""
        try:
            now = datetime.utcnow()
            
            # Get recent tweet times
            recent_tweets = await self.database.get_recent_tweet_times(days=1)
            
            # If we haven't reached today's limit, find next optimal time
            today_tweets = [t for t in recent_tweets if t.date() == now.date()]
            
            if len(today_tweets) < self.tweets_per_day:
                # Find next optimal hour today
                next_slot = self._find_next_optimal_hour(now)
                
                # Make sure it's not too soon after last tweet
                if recent_tweets:
                    last_tweet = max(recent_tweets)
                    min_next_time = last_tweet + timedelta(hours=self.min_interval_hours)
                    next_slot = max(next_slot, min_next_time)
                
                return next_slot
            else:
                # Schedule for tomorrow
                tomorrow = now.replace(hour=self.optimal_hours[0], minute=0, second=0, microsecond=0) + timedelta(days=1)
                return tomorrow
                
        except Exception as e:
            logger.error("Error calculating next slot", error=str(e))
            # Fallback to 2 hours from now
            return datetime.utcnow() + timedelta(hours=2)
    
    def _find_next_optimal_hour(self, from_time: datetime) -> datetime:
        """Find the next optimal posting hour."""
        target_date = from_time.date()
        
        for hour in self.optimal_hours:
            candidate_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
            candidate_time = candidate_time.replace(tzinfo=timezone.utc).replace(tzinfo=None)
            
            if candidate_time > from_time:
                return candidate_time
        
        # If all optimal hours for today have passed, use first hour of tomorrow
        tomorrow = target_date + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time().replace(hour=self.optimal_hours[0]))
    
    def _sort_queue(self):
        """Sort the tweet queue by priority and scheduled time."""
        self.tweet_queue.sort(key=lambda t: (
            -t.priority,  # Higher priority first
            t.scheduled_for or datetime.max,  # Earlier scheduled time first
            t.created_at  # Earlier created time as tiebreaker
        ))
    
    def _load_queue(self) -> List[QueuedTweet]:
        """Load tweet queue from file."""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    queue_data = json.load(f)
                    return [QueuedTweet.from_dict(item) for item in queue_data]
            return []
        except Exception as e:
            logger.error("Failed to load tweet queue", error=str(e))
            return []
    
    def _save_queue(self):
        """Save tweet queue to file."""
        try:
            queue_data = [tweet.to_dict() for tweet in self.tweet_queue]
            with open(self.queue_file, 'w') as f:
                json.dump(queue_data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save tweet queue", error=str(e))
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            now = datetime.utcnow()
            
            total_queued = len(self.tweet_queue)
            ready_to_post = sum(1 for t in self.tweet_queue 
                              if t.scheduled_for and t.scheduled_for <= now)
            
            next_tweet_time = None
            if self.tweet_queue:
                next_tweet = min(self.tweet_queue, 
                               key=lambda t: t.scheduled_for or datetime.max)
                if next_tweet.scheduled_for:
                    next_tweet_time = next_tweet.scheduled_for.isoformat()
            
            # Get recent posting stats
            recent_tweets = await self.database.get_recent_tweet_times(days=7)
            today_tweets = [t for t in recent_tweets if t.date() == now.date()]
            
            return {
                'total_queued': total_queued,
                'ready_to_post': ready_to_post,
                'next_tweet_time': next_tweet_time,
                'tweets_today': len(today_tweets),
                'tweets_this_week': len(recent_tweets),
                'daily_limit': self.tweets_per_day,
                'min_interval_hours': self.min_interval_hours
            }
            
        except Exception as e:
            logger.error("Failed to get queue status", error=str(e))
            return {}
    
    async def clear_queue(self, keep_high_priority: bool = True) -> int:
        """Clear the tweet queue."""
        try:
            original_count = len(self.tweet_queue)
            
            if keep_high_priority:
                self.tweet_queue = [t for t in self.tweet_queue if t.priority > 1]
                removed_count = original_count - len(self.tweet_queue)
            else:
                self.tweet_queue.clear()
                removed_count = original_count
            
            self._save_queue()
            
            logger.info("Queue cleared", 
                       removed_count=removed_count,
                       remaining_count=len(self.tweet_queue))
            
            return removed_count
            
        except Exception as e:
            logger.error("Failed to clear queue", error=str(e))
            return 0
    
    async def reschedule_tweet(self, tweet_id: str, new_time: datetime) -> bool:
        """Reschedule a specific tweet."""
        try:
            for tweet in self.tweet_queue:
                if tweet.id == tweet_id:
                    tweet.scheduled_for = new_time
                    self._sort_queue()
                    self._save_queue()
                    
                    logger.info("Tweet rescheduled", 
                               tweet_id=tweet_id,
                               new_time=new_time.isoformat())
                    return True
            
            logger.warning("Tweet not found for rescheduling", tweet_id=tweet_id)
            return False
            
        except Exception as e:
            logger.error("Failed to reschedule tweet", 
                        tweet_id=tweet_id, error=str(e))
            return False
    
    async def remove_tweet(self, tweet_id: str) -> bool:
        """Remove a specific tweet from the queue."""
        try:
            original_count = len(self.tweet_queue)
            self.tweet_queue = [t for t in self.tweet_queue if t.id != tweet_id]
            
            if len(self.tweet_queue) < original_count:
                self._save_queue()
                logger.info("Tweet removed from queue", tweet_id=tweet_id)
                return True
            else:
                logger.warning("Tweet not found for removal", tweet_id=tweet_id)
                return False
                
        except Exception as e:
            logger.error("Failed to remove tweet", tweet_id=tweet_id, error=str(e))
            return False
    
    async def update_posting_schedule(self, tweets_per_day: int, optimal_hours: List[int]):
        """Update the posting schedule configuration."""
        try:
            self.tweets_per_day = tweets_per_day
            self.optimal_hours = optimal_hours
            self.min_interval_hours = max(24 // tweets_per_day - 1, 2)
            
            # Reschedule existing tweets
            for tweet in self.tweet_queue:
                if tweet.scheduled_for:
                    new_time = await self._calculate_next_slot()
                    tweet.scheduled_for = new_time
            
            self._sort_queue()
            self._save_queue()
            
            logger.info("Posting schedule updated", 
                       tweets_per_day=tweets_per_day,
                       optimal_hours=optimal_hours)
            
        except Exception as e:
            logger.error("Failed to update posting schedule", error=str(e))
    
    async def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get posting analytics for the specified period."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get posted tweets
            posted_tweets = await self.database.get_posted_tweets_since(cutoff_date)
            
            # Calculate metrics
            total_posted = len(posted_tweets)
            avg_per_day = total_posted / days if days > 0 else 0
            
            # Group by day
            daily_counts = {}
            for tweet in posted_tweets:
                day = tweet['posted_at'].date()
                daily_counts[day] = daily_counts.get(day, 0) + 1
            
            # Get engagement metrics from Twitter
            engagement_metrics = await self.twitter_client.get_engagement_metrics(days=days)
            
            return {
                'period_days': days,
                'total_posted': total_posted,
                'average_per_day': round(avg_per_day, 1),
                'daily_counts': {str(k): v for k, v in daily_counts.items()},
                'engagement': engagement_metrics,
                'queue_size': len(self.tweet_queue)
            }
            
        except Exception as e:
            logger.error("Failed to get analytics", error=str(e))
            return {}
