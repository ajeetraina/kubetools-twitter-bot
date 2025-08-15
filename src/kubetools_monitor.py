"""
Kubetools Repository Monitor

This module monitors the kubetools repository for new Kubernetes tools
and extracts information about newly added tools.

Author: Ajeet Singh Raina
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import requests
import structlog
from github import Github, GithubException

logger = structlog.get_logger()


@dataclass
class KubeTool:
    """Data class representing a Kubernetes tool."""
    name: str
    description: str
    url: str
    github_url: Optional[str]
    stars: int
    category: str
    added_date: datetime
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None


class KubetoolsMonitor:
    """Monitors the kubetools repository for new tool additions."""
    
    def __init__(self, github_token: str, database):
        """Initialize the monitor with GitHub token and database."""
        self.github_token = github_token
        self.database = database
        self.github = Github(github_token)
        self.repo_name = "collabnix/kubetools"
        self.repo = self.github.get_repo(self.repo_name)
        
        # Regular expressions for parsing tool entries
        self.tool_pattern = re.compile(
            r'\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)[^|]*\|\s*!\[Github Stars\]'
        )
        self.github_url_pattern = re.compile(r'github\.com/([^/]+/[^/)]+)')
        
        logger.info("KubetoolsMonitor initialized", repo=self.repo_name)
    
    async def check_for_new_tools(self) -> List[Dict[str, Any]]:
        """Check for new tools added to the repository."""
        try:
            # Get the latest commit timestamp from our database
            last_check = await self.database.get_last_check_timestamp()
            
            # Get recent commits since last check
            commits = self._get_recent_commits(since=last_check)
            
            new_tools = []
            for commit in commits:
                tools_in_commit = await self._extract_tools_from_commit(commit)
                for tool in tools_in_commit:
                    # Check if tool is already in database
                    if not await self.database.tool_exists(tool.name, tool.url):
                        new_tools.append(self._tool_to_dict(tool))
                        await self.database.add_tool(tool)
            
            # Update last check timestamp
            await self.database.update_last_check_timestamp()
            
            logger.info(f"Found {len(new_tools)} new tools", count=len(new_tools))
            return new_tools
            
        except Exception as e:
            logger.error("Failed to check for new tools", error=str(e))
            return []
    
    def _get_recent_commits(self, since: Optional[datetime] = None) -> List:
        """Get recent commits from the repository."""
        try:
            if since is None:
                since = datetime.utcnow() - timedelta(days=7)  # Default to last week
            
            commits = list(self.repo.get_commits(
                since=since,
                path="README.md"  # Only check commits that modify README.md
            ))
            
            logger.info(f"Retrieved {len(commits)} recent commits", 
                       since=since.isoformat(), count=len(commits))
            return commits
            
        except GithubException as e:
            logger.error("GitHub API error while fetching commits", error=str(e))
            return []
    
    async def _extract_tools_from_commit(self, commit) -> List[KubeTool]:
        """Extract new tools from a commit."""
        try:
            # Get the commit diff
            files = commit.files
            tools = []
            
            for file in files:
                if file.filename == "README.md" and file.status in ["modified", "added"]:
                    # Parse additions in the diff
                    if hasattr(file, 'patch') and file.patch:
                        added_lines = self._get_added_lines(file.patch)
                        for line in added_lines:
                            tool = self._parse_tool_line(line, commit)
                            if tool:
                                tools.append(tool)
            
            logger.info(f"Extracted {len(tools)} tools from commit", 
                       commit_sha=commit.sha[:8], count=len(tools))
            return tools
            
        except Exception as e:
            logger.error("Failed to extract tools from commit", 
                        commit_sha=commit.sha[:8], error=str(e))
            return []
    
    def _get_added_lines(self, patch: str) -> List[str]:
        """Extract added lines from a git patch."""
        added_lines = []
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])  # Remove the '+' prefix
        return added_lines
    
    def _parse_tool_line(self, line: str, commit) -> Optional[KubeTool]:
        """Parse a tool entry from a line in the README."""
        try:
            # Match tool table entry pattern
            match = self.tool_pattern.search(line)
            if not match:
                return None
            
            sr_no, tool_name, description, url = match.groups()
            
            # Clean up the data
            tool_name = tool_name.strip()
            description = description.strip()
            url = url.strip()
            
            # Determine category based on context (you might want to improve this)
            category = self._determine_category(line, description)
            
            # Extract GitHub URL and get stars
            github_url = None
            stars = 0
            
            github_match = self.github_url_pattern.search(url)
            if github_match:
                github_url = f"https://github.com/{github_match.group(1)}"
                stars = self._get_github_stars(github_match.group(1))
            
            return KubeTool(
                name=tool_name,
                description=description,
                url=url,
                github_url=github_url,
                stars=stars,
                category=category,
                added_date=commit.commit.committer.date,
                commit_sha=commit.sha
            )
            
        except Exception as e:
            logger.error("Failed to parse tool line", line=line[:100], error=str(e))
            return None
    
    def _determine_category(self, line: str, description: str) -> str:
        """Determine the category of a tool based on context."""
        # This is a simplified categorization - you might want to improve this
        # based on the section headers in the README
        
        categories = {
            'monitoring': ['monitor', 'observability', 'metrics', 'alert'],
            'security': ['security', 'scan', 'vulnerability', 'policy'],
            'networking': ['network', 'ingress', 'service mesh', 'proxy'],
            'storage': ['storage', 'volume', 'backup', 'database'],
            'development': ['development', 'dev', 'build', 'ci/cd'],
            'debugging': ['debug', 'troubleshoot', 'log', 'trace'],
            'deployment': ['deploy', 'helm', 'operator', 'install'],
            'cluster': ['cluster', 'node', 'management'],
            'ai': ['ai', 'machine learning', 'ml', 'artificial'],
        }
        
        description_lower = description.lower()
        for category, keywords in categories.items():
            if any(keyword in description_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def _get_github_stars(self, repo_path: str) -> int:
        """Get GitHub stars for a repository."""
        try:
            repo = self.github.get_repo(repo_path)
            return repo.stargazers_count
        except Exception as e:
            logger.warning("Failed to get GitHub stars", repo=repo_path, error=str(e))
            return 0
    
    def _tool_to_dict(self, tool: KubeTool) -> Dict[str, Any]:
        """Convert KubeTool to dictionary."""
        return {
            'name': tool.name,
            'description': tool.description,
            'url': tool.url,
            'github_url': tool.github_url,
            'stars': tool.stars,
            'category': tool.category,
            'added_date': tool.added_date.isoformat(),
            'commit_sha': tool.commit_sha
        }
    
    async def get_tool_statistics(self) -> Dict[str, Any]:
        """Get statistics about tools in the repository."""
        try:
            # Get current README content
            readme = self.repo.get_contents("README.md")
            content = readme.decoded_content.decode('utf-8')
            
            # Count tools by category
            all_tools = self._parse_all_tools(content)
            
            category_counts = {}
            for tool in all_tools:
                category = tool.category
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                'total_tools': len(all_tools),
                'categories': category_counts,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get tool statistics", error=str(e))
            return {}
    
    def _parse_all_tools(self, content: str) -> List[KubeTool]:
        """Parse all tools from README content."""
        tools = []
        for line in content.split('\n'):
            tool = self._parse_tool_line(line, None)
            if tool:
                tools.append(tool)
        return tools
    
    async def health_check(self) -> bool:
        """Perform health check on GitHub API connectivity."""
        try:
            # Try to get repository info
            repo_info = self.repo.get_repo()
            logger.info("GitHub API health check passed", 
                       repo=repo_info.full_name)
            return True
        except Exception as e:
            logger.error("GitHub API health check failed", error=str(e))
            return False
    
    async def get_recent_prs(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent pull requests that might contain new tools."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            pulls = self.repo.get_pulls(
                state='all',
                sort='updated',
                direction='desc'
            )
            
            recent_prs = []
            for pr in pulls:
                if pr.updated_at >= since:
                    recent_prs.append({
                        'number': pr.number,
                        'title': pr.title,
                        'user': pr.user.login,
                        'state': pr.state,
                        'created_at': pr.created_at.isoformat(),
                        'updated_at': pr.updated_at.isoformat(),
                        'html_url': pr.html_url
                    })
            
            logger.info(f"Found {len(recent_prs)} recent PRs", count=len(recent_prs))
            return recent_prs
            
        except Exception as e:
            logger.error("Failed to get recent PRs", error=str(e))
            return []
