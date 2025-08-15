"""
Tweet Generator

This module generates engaging tweets about new Kubernetes tools.

Author: Ajeet Singh Raina
"""

import random
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger()


class TweetGenerator:
    """Generates engaging tweets about Kubernetes tools."""
    
    def __init__(self):
        """Initialize the tweet generator with templates and patterns."""
        self.tweet_templates = self._load_tweet_templates()
        self.hashtags = self._load_hashtags()
        self.emojis = self._load_emojis()
        
        logger.info("Tweet generator initialized")
    
    def _load_tweet_templates(self) -> Dict[str, List[str]]:
        """Load tweet templates for different scenarios."""
        return {
            'new_tool': [
                "🚀 New #Kubernetes tool: {name}\n\n{description}\n\n⭐ {stars} stars\n🔗 {url}\n\n{category_tags} #DevOps #CloudNative #K8s",
                "📢 Discover {name} - a new #Kubernetes tool!\n\n✨ {description}\n\n👉 {url}\n⭐ {stars} GitHub stars\n\n{category_tags} #K8s #DevOps",
                "🎯 {name} just joined the #Kubernetes ecosystem!\n\n{description}\n\n🌟 {stars} stars and growing\n📦 {url}\n\n{category_tags} #CloudNative #DevOps",
                "⚡ Fresh #Kubernetes tool alert: {name}\n\n{description}\n\n✅ {stars} GitHub stars\n🔧 {url}\n\n{category_tags} #K8s #DevOps #OpenSource",
                "🔥 Hot new #Kubernetes tool: {name}\n\n{short_description}\n\n💫 {stars} stars\n📋 {url}\n\n{category_tags} #Kubernetes #DevOps",
                "🛠️ Meet {name}: {short_description}\n\nPerfect for your #Kubernetes toolkit!\n\n⭐ {stars} stars\n🚀 {url}\n\n{category_tags} #CloudNative #DevOps",
                "🎉 {name} is now part of the #kubetools collection!\n\n{description}\n\n🌟 {stars} GitHub stars\n📖 {url}\n\n{category_tags} #Kubernetes #DevOps",
                "💡 Introducing {name}: {short_description}\n\nGreat addition to the #Kubernetes ecosystem!\n\n⭐ {stars} stars\n🔗 {url}\n\n{category_tags}"
            ],
            'trending_tool': [
                "📈 Trending: {name} is gaining momentum in the #Kubernetes community!\n\n{description}\n\n🚀 {stars} stars\n👀 {url}\n\n{category_tags} #DevOps",
                "🔥 {name} is on fire! 🔥\n\n{description}\n\n⭐ {stars} stars and counting\n📦 {url}\n\n{category_tags} #Kubernetes #Trending"
            ],
            'category_spotlight': [
                "🎯 #{category} spotlight: {name}\n\n{description}\n\n✨ {stars} stars\n🔗 {url}\n\n{category_tags} #Kubernetes #DevOps",
                "🔍 Featured #{category} tool: {name}\n\n{description}\n\n⭐ {stars} GitHub stars\n📋 {url}\n\n{category_tags} #K8s"
            ]
        }
    
    def _load_hashtags(self) -> Dict[str, List[str]]:
        """Load category-specific hashtags."""
        return {
            'monitoring': ['#Monitoring', '#Observability', '#Metrics', '#AlertManager'],
            'security': ['#Security', '#DevSecOps', '#K8sSecurity', '#PolicyEngine'],
            'networking': ['#Networking', '#ServiceMesh', '#Ingress', '#CNI'],
            'storage': ['#Storage', '#PersistentVolumes', '#StatefulSets', '#Backup'],
            'development': ['#Development', '#DevTools', '#LocalDev', '#InnerLoop'],
            'debugging': ['#Debugging', '#Troubleshooting', '#Logging', '#Tracing'],
            'deployment': ['#Deployment', '#Helm', '#Operators', '#GitOps'],
            'cluster': ['#ClusterManagement', '#NodeManagement', '#Infrastructure'],
            'ai': ['#AI', '#MachineLearning', '#MLOps', '#KubeFlow'],
            'general': ['#Tools', '#Utilities', '#Productivity'],
            'cicd': ['#CICD', '#Pipeline', '#Automation', '#GitOps'],
            'testing': ['#Testing', '#QA', '#ChaosEngineering'],
            'backup': ['#Backup', '#DisasterRecovery', '#DataProtection'],
            'cost': ['#CostOptimization', '#FinOps', '#ResourceManagement']
        }
    
    def _load_emojis(self) -> Dict[str, List[str]]:
        """Load category-specific emojis."""
        return {
            'monitoring': ['📊', '📈', '👀', '🔍', '📡'],
            'security': ['🔒', '🛡️', '🔐', '🚨', '⚡'],
            'networking': ['🌐', '🔗', '📡', '🌉', '📶'],
            'storage': ['💾', '📦', '🗄️', '💿', '📚'],
            'development': ['👨‍💻', '💻', '🛠️', '⚙️', '🔧'],
            'debugging': ['🐛', '🔍', '🕵️', '📋', '🩺'],
            'deployment': ['🚀', '📦', '🎯', '⚡', '🔄'],
            'cluster': ['🏗️', '🖥️', '⚙️', '🔧', '🏭'],
            'ai': ['🤖', '🧠', '⚡', '🎯', '🔮'],
            'general': ['🛠️', '⚙️', '🔧', '📦', '✨'],
            'cicd': ['🔄', '⚡', '🚀', '📦', '🎯'],
            'testing': ['🧪', '✅', '🔬', '🎯', '⚡'],
            'backup': ['💾', '🔄', '📦', '💿', '🛡️'],
            'cost': ['💰', '📊', '📉', '⚡', '🎯']
        }
    
    def generate_tweet(self, tool: Dict[str, Any], tweet_type: str = 'new_tool') -> str:
        """Generate a tweet for a tool."""
        try:
            logger.info("Generating tweet", 
                       tool_name=tool.get('name', 'Unknown'),
                       tweet_type=tweet_type)
            
            # Get template
            templates = self.tweet_templates.get(tweet_type, self.tweet_templates['new_tool'])
            template = random.choice(templates)
            
            # Prepare tweet data
            tweet_data = self._prepare_tweet_data(tool)
            
            # Format tweet
            tweet = template.format(**tweet_data)
            
            # Ensure tweet length is within limits
            tweet = self._ensure_tweet_length(tweet)
            
            logger.info("Tweet generated successfully", 
                       length=len(tweet),
                       tool_name=tool.get('name', 'Unknown'))
            
            return tweet
            
        except Exception as e:
            logger.error("Failed to generate tweet", 
                        tool_name=tool.get('name', 'Unknown'),
                        error=str(e))
            return self._generate_fallback_tweet(tool)
    
    def _prepare_tweet_data(self, tool: Dict[str, Any]) -> Dict[str, str]:
        """Prepare data for tweet formatting."""
        name = tool.get('name', 'Unknown Tool')
        description = tool.get('description', 'A new Kubernetes tool')
        url = tool.get('url', tool.get('github_url', ''))
        stars = tool.get('stars', 0)
        category = tool.get('category', 'general')
        
        # Format stars with proper formatting
        stars_formatted = self._format_stars(stars)
        
        # Clean and truncate description
        description_clean = self._clean_description(description)
        short_description = self._create_short_description(description_clean)
        
        # Get category-specific hashtags
        category_tags = self._get_category_hashtags(category)
        
        # Get category emoji
        category_emoji = self._get_category_emoji(category)
        
        return {
            'name': name,
            'description': description_clean,
            'short_description': short_description,
            'url': url,
            'stars': stars_formatted,
            'category': category.title(),
            'category_tags': category_tags,
            'category_emoji': category_emoji
        }
    
    def _format_stars(self, stars: int) -> str:
        """Format star count for display."""
        if stars >= 1000:
            return f"{stars/1000:.1f}k"
        return str(stars)
    
    def _clean_description(self, description: str) -> str:
        """Clean and format tool description."""
        # Remove URLs
        description = re.sub(r'http[s]?://\S+', '', description)
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Ensure it ends with proper punctuation
        if description and not description.endswith(('.', '!', '?')):
            description += '.'
        
        return description
    
    def _create_short_description(self, description: str) -> str:
        """Create a shorter version of the description."""
        if len(description) <= 80:
            return description
        
        # Try to cut at sentence boundary
        sentences = description.split('. ')
        if sentences and len(sentences[0]) <= 80:
            return sentences[0] + '.'
        
        # Cut at word boundary
        words = description.split()
        short_desc = ""
        for word in words:
            if len(short_desc + word) > 75:
                break
            short_desc += word + " "
        
        return short_desc.strip() + "..."
    
    def _get_category_hashtags(self, category: str) -> str:
        """Get hashtags for a category."""
        hashtags = self.hashtags.get(category, self.hashtags['general'])
        # Select 2-3 relevant hashtags
        selected = random.sample(hashtags, min(3, len(hashtags)))
        return ' '.join(selected)
    
    def _get_category_emoji(self, category: str) -> str:
        """Get an emoji for a category."""
        emojis = self.emojis.get(category, self.emojis['general'])
        return random.choice(emojis)
    
    def _ensure_tweet_length(self, tweet: str, max_length: int = 280) -> str:
        """Ensure tweet is within character limit."""
        if len(tweet) <= max_length:
            return tweet
        
        # Try to trim description first
        lines = tweet.split('\n')
        if len(lines) >= 3:  # Has name, description, and other info
            description_line = lines[2] if len(lines) > 2 else lines[1]
            
            # Calculate available space for description
            other_lines_length = sum(len(line) for i, line in enumerate(lines) if i != 2)
            newlines_count = len(lines) - 1
            available_space = max_length - other_lines_length - newlines_count
            
            if available_space > 20:  # Minimum reasonable description length
                # Trim description
                trimmed_desc = description_line[:available_space-3] + "..."
                lines[2] = trimmed_desc
                return '\n'.join(lines)
        
        # If still too long, use a simple fallback
        return tweet[:max_length-3] + "..."
    
    def _generate_fallback_tweet(self, tool: Dict[str, Any]) -> str:
        """Generate a simple fallback tweet."""
        name = tool.get('name', 'New Tool')
        url = tool.get('url', tool.get('github_url', ''))
        stars = tool.get('stars', 0)
        
        return f"🚀 New #Kubernetes tool: {name}\n\n⭐ {self._format_stars(stars)} stars\n🔗 {url}\n\n#DevOps #CloudNative #K8s"
    
    def generate_thread(self, tools: List[Dict[str, Any]], 
                       intro_text: str = "🧵 Thread: New #Kubernetes tools this week!") -> List[str]:
        """Generate a Twitter thread for multiple tools."""
        try:
            tweets = [intro_text]
            
            for i, tool in enumerate(tools, 1):
                # Create numbered tweet for thread
                thread_tweet = f"{i}/{len(tools)} 🧵\n\n"
                
                # Generate regular tweet content
                tool_tweet = self.generate_tweet(tool)
                
                # Remove intro emoji and hashtags to save space
                tool_lines = tool_tweet.split('\n')
                if tool_lines:
                    # Remove first emoji/intro
                    first_line = tool_lines[0]
                    if first_line.startswith('🚀') or first_line.startswith('📢'):
                        tool_lines[0] = first_line.split(' ', 1)[1] if ' ' in first_line else first_line
                
                thread_tweet += '\n'.join(tool_lines)
                
                # Ensure thread tweet length
                thread_tweet = self._ensure_tweet_length(thread_tweet)
                tweets.append(thread_tweet)
            
            logger.info(f"Generated thread with {len(tweets)} tweets", 
                       thread_length=len(tweets),
                       tools_count=len(tools))
            
            return tweets
            
        except Exception as e:
            logger.error("Failed to generate thread", error=str(e))
            # Return simple fallback thread
            return [
                intro_text,
                f"Check out these new #Kubernetes tools! {' '.join([tool.get('url', '') for tool in tools[:3]])}"
            ]
    
    def generate_weekly_summary(self, tools: List[Dict[str, Any]]) -> str:
        """Generate a weekly summary tweet."""
        try:
            tool_count = len(tools)
            categories = {}
            total_stars = 0
            
            for tool in tools:
                category = tool.get('category', 'general')
                categories[category] = categories.get(category, 0) + 1
                total_stars += tool.get('stars', 0)
            
            top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
            
            summary = f"📊 Weekly #Kubernetes tools recap:\n\n"
            summary += f"🆕 {tool_count} new tools added\n"
            summary += f"⭐ {total_stars:,} total GitHub stars\n"
            summary += f"📂 Top categories: {', '.join([cat.title() for cat, _ in top_categories])}\n\n"
            summary += f"🔗 See all tools: https://kubetools.io\n\n"
            summary += f"#DevOps #CloudNative #K8s #OpenSource"
            
            logger.info("Generated weekly summary", tool_count=tool_count)
            return summary
            
        except Exception as e:
            logger.error("Failed to generate weekly summary", error=str(e))
            return "📊 Weekly #Kubernetes tools recap - check out the latest additions! 🚀 #DevOps #K8s"
    
    def validate_tweet(self, tweet: str) -> Dict[str, Any]:
        """Validate a tweet for common issues."""
        validation = {
            'valid': True,
            'issues': [],
            'length': len(tweet),
            'has_hashtags': bool(re.search(r'#\w+', tweet)),
            'has_url': bool(re.search(r'http[s]?://\S+', tweet)),
            'has_emoji': bool(re.search(r'[\U00010000-\U0010ffff]|[\u2600-\u27ff]', tweet))
        }
        
        if len(tweet) > 280:
            validation['valid'] = False
            validation['issues'].append('Tweet too long')
        
        if len(tweet) < 10:
            validation['valid'] = False
            validation['issues'].append('Tweet too short')
        
        if not validation['has_hashtags']:
            validation['issues'].append('No hashtags found')
        
        if not validation['has_url']:
            validation['issues'].append('No URL found')
        
        return validation
