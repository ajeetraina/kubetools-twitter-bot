"""
Database Module

This module handles data persistence for the kubetools Twitter bot,
including tool tracking, tweet history, and state management.

Author: Ajeet Singh Raina
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ToolRecord:
    """Represents a tool record in the database."""
    name: str
    url: str
    github_url: Optional[str]
    description: str
    category: str
    stars: int
    added_date: datetime
    commit_sha: Optional[str] = None
    first_seen: Optional[datetime] = None


class Database:
    """Handles all database operations for the bot."""
    
    def __init__(self, db_path: str = "data/kubetools_bot.db"):
        """Initialize the database connection."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Fallback to JSON files if SQLite is not available
        self.use_json_fallback = False
        self.json_data_dir = Path("data")
        self.json_data_dir.mkdir(exist_ok=True)
        
        try:
            self._init_database()
        except Exception as e:
            logger.warning("Failed to initialize SQLite, falling back to JSON", error=str(e))
            self.use_json_fallback = True
            self._init_json_storage()
        
        logger.info("Database initialized", 
                   storage_type="JSON" if self.use_json_fallback else "SQLite",
                   path=str(self.db_path if not self.use_json_fallback else self.json_data_dir))
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    github_url TEXT,
                    description TEXT,
                    category TEXT,
                    stars INTEGER DEFAULT 0,
                    added_date TEXT NOT NULL,
                    commit_sha TEXT,
                    first_seen TEXT NOT NULL,
                    UNIQUE(name, url)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_tweets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT UNIQUE NOT NULL,
                    twitter_id TEXT,
                    tool_name TEXT,
                    content TEXT NOT NULL,
                    posted_at TEXT NOT NULL,
                    engagement_data TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queued_tweets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT UNIQUE NOT NULL,
                    tool_data TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    scheduled_for TEXT,
                    priority INTEGER DEFAULT 1,
                    attempts INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def _init_json_storage(self):
        """Initialize JSON file storage as fallback."""
        self.json_files = {
            'tools': self.json_data_dir / 'tools.json',
            'posted_tweets': self.json_data_dir / 'posted_tweets.json',
            'queued_tweets': self.json_data_dir / 'queued_tweets.json',
            'bot_state': self.json_data_dir / 'bot_state.json'
        }
        
        for file_path in self.json_files.values():
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def _load_json_data(self, file_key: str) -> List[Dict[str, Any]]:
        """Load data from JSON file."""
        try:
            with open(self.json_files[file_key], 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {file_key} JSON data", error=str(e))
            return []
    
    def _save_json_data(self, file_key: str, data: List[Dict[str, Any]]):
        """Save data to JSON file."""
        try:
            with open(self.json_files[file_key], 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save {file_key} JSON data", error=str(e))
    
    async def tool_exists(self, name: str, url: str) -> bool:
        """Check if a tool already exists in the database."""
        try:
            if self.use_json_fallback:
                tools = self._load_json_data('tools')
                return any(tool['name'] == name and tool['url'] == url for tool in tools)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM tools WHERE name = ? AND url = ?",
                        (name, url)
                    )
                    return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error("Failed to check if tool exists", 
                        name=name, url=url, error=str(e))
            return False
    
    async def add_tool(self, tool) -> bool:
        """Add a new tool to the database."""
        try:
            tool_data = {
                'name': tool.name,
                'url': tool.url,
                'github_url': tool.github_url,
                'description': tool.description,
                'category': tool.category,
                'stars': tool.stars,
                'added_date': tool.added_date.isoformat(),
                'commit_sha': tool.commit_sha,
                'first_seen': datetime.utcnow().isoformat()
            }
            
            if self.use_json_fallback:
                tools = self._load_json_data('tools')
                tools.append(tool_data)
                self._save_json_data('tools', tools)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR IGNORE INTO tools 
                        (name, url, github_url, description, category, stars, added_date, commit_sha, first_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        tool.name, tool.url, tool.github_url, tool.description,
                        tool.category, tool.stars, tool.added_date.isoformat(),
                        tool.commit_sha, datetime.utcnow().isoformat()
                    ))
                    conn.commit()
            
            logger.info("Tool added to database", name=tool.name)
            return True
            
        except Exception as e:
            logger.error("Failed to add tool", name=tool.name, error=str(e))
            return False
    
    async def get_total_tools_count(self) -> int:
        """Get the total number of tools tracked."""
        try:
            if self.use_json_fallback:
                tools = self._load_json_data('tools')
                return len(tools)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM tools")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error("Failed to get tools count", error=str(e))
            return 0
    
    async def add_queued_tweet(self, queued_tweet) -> bool:
        """Add a tweet to the queue tracking."""
        try:
            tweet_data = {
                'tweet_id': queued_tweet.id,
                'tool_data': json.dumps(queued_tweet.tool_data),
                'content': queued_tweet.tweet_content,
                'created_at': queued_tweet.created_at.isoformat(),
                'scheduled_for': queued_tweet.scheduled_for.isoformat() if queued_tweet.scheduled_for else None,
                'priority': queued_tweet.priority,
                'attempts': queued_tweet.attempts
            }
            
            if self.use_json_fallback:
                queued_tweets = self._load_json_data('queued_tweets')
                queued_tweets.append(tweet_data)
                self._save_json_data('queued_tweets', queued_tweets)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO queued_tweets 
                        (tweet_id, tool_data, content, created_at, scheduled_for, priority, attempts)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        queued_tweet.id, json.dumps(queued_tweet.tool_data),
                        queued_tweet.tweet_content, queued_tweet.created_at.isoformat(),
                        queued_tweet.scheduled_for.isoformat() if queued_tweet.scheduled_for else None,
                        queued_tweet.priority, queued_tweet.attempts
                    ))
                    conn.commit()
            
            return True
            
        except Exception as e:
            logger.error("Failed to add queued tweet", error=str(e))
            return False
    
    async def get_queued_tweets_count(self) -> int:
        """Get the number of tweets in queue."""
        try:
            if self.use_json_fallback:
                queued_tweets = self._load_json_data('queued_tweets')
                return len(queued_tweets)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM queued_tweets")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error("Failed to get queued tweets count", error=str(e))
            return 0
    
    async def mark_tweet_posted(self, tweet_id: str, twitter_result: Dict[str, Any]) -> bool:
        """Mark a tweet as posted and store the result."""
        try:
            posted_data = {
                'tweet_id': tweet_id,
                'twitter_id': twitter_result.get('id'),
                'tool_name': twitter_result.get('tool_name', 'Unknown'),
                'content': twitter_result.get('text', ''),
                'posted_at': datetime.utcnow().isoformat(),
                'engagement_data': json.dumps({})
            }
            
            if self.use_json_fallback:
                posted_tweets = self._load_json_data('posted_tweets')
                posted_tweets.append(posted_data)
                self._save_json_data('posted_tweets', posted_tweets)
                
                # Remove from queued tweets
                queued_tweets = self._load_json_data('queued_tweets')
                queued_tweets = [t for t in queued_tweets if t['tweet_id'] != tweet_id]
                self._save_json_data('queued_tweets', queued_tweets)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO posted_tweets 
                        (tweet_id, twitter_id, tool_name, content, posted_at, engagement_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        tweet_id, twitter_result.get('id'), 
                        twitter_result.get('tool_name', 'Unknown'),
                        twitter_result.get('text', ''), 
                        datetime.utcnow().isoformat(),
                        json.dumps({})
                    ))
                    
                    # Remove from queued tweets
                    conn.execute("DELETE FROM queued_tweets WHERE tweet_id = ?", (tweet_id,))
                    conn.commit()
            
            return True
            
        except Exception as e:
            logger.error("Failed to mark tweet as posted", tweet_id=tweet_id, error=str(e))
            return False
    
    async def mark_tweet_failed(self, tweet_id: str) -> bool:
        """Mark a tweet as failed and remove from queue."""
        try:
            if self.use_json_fallback:
                queued_tweets = self._load_json_data('queued_tweets')
                queued_tweets = [t for t in queued_tweets if t['tweet_id'] != tweet_id]
                self._save_json_data('queued_tweets', queued_tweets)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM queued_tweets WHERE tweet_id = ?", (tweet_id,))
                    conn.commit()
            
            logger.info("Tweet marked as failed and removed", tweet_id=tweet_id)
            return True
            
        except Exception as e:
            logger.error("Failed to mark tweet as failed", tweet_id=tweet_id, error=str(e))
            return False
    
    async def get_posted_tweets_count(self) -> int:
        """Get the total number of posted tweets."""
        try:
            if self.use_json_fallback:
                posted_tweets = self._load_json_data('posted_tweets')
                return len(posted_tweets)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM posted_tweets")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error("Failed to get posted tweets count", error=str(e))
            return 0
    
    async def get_last_check_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the last repository check."""
        try:
            value = await self._get_state_value('last_check_timestamp')
            if value:
                return datetime.fromisoformat(value)
            return None
        except Exception as e:
            logger.error("Failed to get last check timestamp", error=str(e))
            return None
    
    async def update_last_check_timestamp(self) -> bool:
        """Update the last repository check timestamp."""
        try:
            return await self._set_state_value(
                'last_check_timestamp', 
                datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error("Failed to update last check timestamp", error=str(e))
            return False
    
    async def get_last_tweet_time(self) -> Optional[datetime]:
        """Get the timestamp of the last posted tweet."""
        try:
            if self.use_json_fallback:
                posted_tweets = self._load_json_data('posted_tweets')
                if posted_tweets:
                    latest = max(posted_tweets, key=lambda t: t['posted_at'])
                    return datetime.fromisoformat(latest['posted_at'])
                return None
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT posted_at FROM posted_tweets ORDER BY posted_at DESC LIMIT 1"
                    )
                    result = cursor.fetchone()
                    if result:
                        return datetime.fromisoformat(result[0])
                    return None
        except Exception as e:
            logger.error("Failed to get last tweet time", error=str(e))
            return None
    
    async def update_last_tweet_time(self) -> bool:
        """Update the last tweet time to now."""
        try:
            return await self._set_state_value(
                'last_tweet_time',
                datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error("Failed to update last tweet time", error=str(e))
            return False
    
    async def get_recent_tweet_times(self, days: int = 7) -> List[datetime]:
        """Get recent tweet times for scheduling purposes."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            if self.use_json_fallback:
                posted_tweets = self._load_json_data('posted_tweets')
                recent_times = []
                for tweet in posted_tweets:
                    posted_at = datetime.fromisoformat(tweet['posted_at'])
                    if posted_at >= cutoff:
                        recent_times.append(posted_at)
                return recent_times
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT posted_at FROM posted_tweets WHERE posted_at >= ? ORDER BY posted_at",
                        (cutoff.isoformat(),)
                    )
                    return [datetime.fromisoformat(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed to get recent tweet times", error=str(e))
            return []
    
    async def get_posted_tweets_since(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get posted tweets since a certain date."""
        try:
            if self.use_json_fallback:
                posted_tweets = self._load_json_data('posted_tweets')
                recent_tweets = []
                for tweet in posted_tweets:
                    posted_at = datetime.fromisoformat(tweet['posted_at'])
                    if posted_at >= cutoff_date:
                        tweet['posted_at'] = posted_at  # Convert back to datetime
                        recent_tweets.append(tweet)
                return recent_tweets
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT tweet_id, twitter_id, tool_name, content, posted_at, engagement_data
                        FROM posted_tweets 
                        WHERE posted_at >= ?
                        ORDER BY posted_at
                    """, (cutoff_date.isoformat(),))
                    
                    tweets = []
                    for row in cursor.fetchall():
                        tweets.append({
                            'tweet_id': row[0],
                            'twitter_id': row[1],
                            'tool_name': row[2],
                            'content': row[3],
                            'posted_at': datetime.fromisoformat(row[4]),
                            'engagement_data': json.loads(row[5] or '{}')
                        })
                    return tweets
        except Exception as e:
            logger.error("Failed to get posted tweets since", error=str(e))
            return []
    
    async def _get_state_value(self, key: str) -> Optional[str]:
        """Get a state value from the database."""
        try:
            if self.use_json_fallback:
                state_data = self._load_json_data('bot_state')
                for item in state_data:
                    if item.get('key') == key:
                        return item.get('value')
                return None
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT value FROM bot_state WHERE key = ?", (key,))
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error("Failed to get state value", key=key, error=str(e))
            return None
    
    async def _set_state_value(self, key: str, value: str) -> bool:
        """Set a state value in the database."""
        try:
            if self.use_json_fallback:
                state_data = self._load_json_data('bot_state')
                # Update existing or add new
                found = False
                for item in state_data:
                    if item.get('key') == key:
                        item['value'] = value
                        item['updated_at'] = datetime.utcnow().isoformat()
                        found = True
                        break
                
                if not found:
                    state_data.append({
                        'key': key,
                        'value': value,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                
                self._save_json_data('bot_state', state_data)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, value, datetime.utcnow().isoformat()))
                    conn.commit()
            
            return True
            
        except Exception as e:
            logger.error("Failed to set state value", key=key, error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """Perform a health check on the database."""
        try:
            if self.use_json_fallback:
                # Check if JSON files are accessible
                for file_path in self.json_files.values():
                    if not file_path.exists():
                        return False
                return True
            else:
                # Test SQLite connection
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {
                'storage_type': 'JSON' if self.use_json_fallback else 'SQLite',
                'total_tools': await self.get_total_tools_count(),
                'queued_tweets': await self.get_queued_tweets_count(),
                'posted_tweets': await self.get_posted_tweets_count(),
                'last_check': await self.get_last_check_timestamp(),
                'last_tweet': await self.get_last_tweet_time()
            }
            
            # Convert datetime objects to strings for JSON serialization
            for key, value in stats.items():
                if isinstance(value, datetime):
                    stats[key] = value.isoformat()
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get database statistics", error=str(e))
            return {}
    
    async def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data from the database."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            cleaned_count = 0
            
            if self.use_json_fallback:
                # Clean up old posted tweets
                posted_tweets = self._load_json_data('posted_tweets')
                original_count = len(posted_tweets)
                posted_tweets = [
                    t for t in posted_tweets 
                    if datetime.fromisoformat(t['posted_at']) >= cutoff
                ]
                cleaned_count = original_count - len(posted_tweets)
                self._save_json_data('posted_tweets', posted_tweets)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM posted_tweets WHERE posted_at < ?",
                        (cutoff.isoformat(),)
                    )
                    cleaned_count = cursor.rowcount
                    conn.commit()
            
            logger.info("Cleaned up old data", 
                       days=days, cleaned_count=cleaned_count)
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
            return 0
