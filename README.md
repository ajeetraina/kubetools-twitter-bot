# Kubetools Twitter Bot 🚀

An automated Twitter bot that monitors the [kubetools repository](https://github.com/collabnix/kubetools) for new Kubernetes tools and tweets about them through [@kubetools](https://x.com/kubetools).

## Features

- 🔍 **Smart Monitoring**: Monitors kubetools repository for new PRs and commits
- 📊 **Change Detection**: Identifies new Kubernetes tools added to the list
- 🐦 **Automated Tweeting**: Posts 3-4 tweets per day about new tools
- 🚫 **Duplicate Prevention**: Maintains state to avoid duplicate tweets
- 📈 **Analytics**: Tracks engagement and tool popularity
- ⏰ **Rate Limiting**: Respects Twitter API limits with intelligent scheduling

## How It Works

1. **Repository Monitoring**: 
   - Watches for new commits and PRs in the kubetools repository
   - Parses README.md changes to identify new tool additions
   - Extracts tool metadata (name, description, GitHub stars, category)

2. **Content Generation**:
   - Creates engaging tweets with tool descriptions
   - Includes relevant hashtags and mentions
   - Adds emojis and formatting for better engagement

3. **Smart Scheduling**:
   - Queues new tools for tweeting
   - Posts 3-4 tweets per day at optimal times
   - Avoids spam and maintains quality

4. **State Management**:
   - Tracks already tweeted tools
   - Maintains a database of tool information
   - Prevents duplicate content

## Repository Structure

```
kubetools-twitter-bot/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-service setup
├── .github/
│   └── workflows/
│       └── twitter-bot.yml     # GitHub Actions workflow
├── src/
│   ├── main.py                 # Main bot application
│   ├── kubetools_monitor.py    # Repository monitoring logic
│   ├── tweet_generator.py      # Tweet content generation
│   ├── twitter_client.py       # Twitter API integration
│   ├── scheduler.py            # Tweet scheduling logic
│   └── database.py             # State management
├── config/
│   ├── config.yaml             # Configuration settings
│   └── templates.yaml          # Tweet templates
├── data/
│   ├── tweeted_tools.json      # Tracking database
│   └── tool_queue.json         # Pending tweets queue
└── tests/
    ├── test_monitor.py         # Unit tests
    ├── test_generator.py       # Unit tests
    └── test_scheduler.py       # Unit tests
```

## Setup Instructions

### Prerequisites

- Python 3.9+
- Twitter Developer Account with API keys
- GitHub Personal Access Token (for monitoring)

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Twitter API Credentials
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# GitHub API
GITHUB_TOKEN=your_github_token

# Bot Configuration
BOT_ENVIRONMENT=production
TWEETS_PER_DAY=4
TIMEZONE=UTC
LOG_LEVEL=INFO

# Database (optional - uses JSON files by default)
DATABASE_URL=sqlite:///kubetools_bot.db
```

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ajeetraina/kubetools-twitter-bot.git
   cd kubetools-twitter-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the bot**:
   ```bash
   python src/main.py
   ```

### Docker Deployment

1. **Using Docker Compose**:
   ```bash
   docker-compose up -d
   ```

2. **Using Docker directly**:
   ```bash
   docker build -t kubetools-twitter-bot .
   docker run -d --env-file .env kubetools-twitter-bot
   ```

### GitHub Actions (Recommended)

The bot runs automatically using GitHub Actions:

- **Schedule**: Runs every 2 hours
- **Trigger**: Can be manually triggered
- **Monitoring**: Checks for new tools and queues tweets
- **Posting**: Posts scheduled tweets at optimal times

## Configuration

### Tweet Templates

Customize tweet templates in `config/templates.yaml`:

```yaml
templates:
  new_tool:
    - "🚀 New #Kubernetes tool: {tool_name}\n\n{description}\n\n⭐ {stars} stars\n🔗 {url}\n\n#DevOps #CloudNative #K8s"
    - "📢 Discover {tool_name} - a new #Kubernetes tool!\n\n✨ {description}\n\n👉 {url}\n⭐ {stars} GitHub stars\n\n#K8s #DevOps"
  
  categories:
    monitoring: "#Monitoring #Observability"
    security: "#Security #DevSecOps"
    networking: "#Networking #ServiceMesh"
    storage: "#Storage #StatefulSets"
```

### Scheduling

Configure posting schedule in `config/config.yaml`:

```yaml
scheduler:
  tweets_per_day: 4
  optimal_hours: [9, 13, 17, 21]  # UTC hours
  timezone: "UTC"
  min_interval_hours: 4
  max_interval_hours: 8
```

## Monitoring and Analytics

### Health Checks

The bot provides health check endpoints:

- `/health` - Basic health status
- `/metrics` - Prometheus metrics
- `/stats` - Bot statistics

### Logs

Structured logging with different levels:

```python
# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Metrics

Track important metrics:

- New tools detected
- Tweets posted
- Engagement rates
- API usage
- Error rates

## API Documentation

### Endpoints

- `GET /api/tools` - List detected tools
- `GET /api/queue` - Show tweet queue
- `POST /api/tweet/{tool_id}` - Manually tweet a tool
- `GET /api/stats` - Bot statistics

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Make changes** and add tests
4. **Run tests**: `pytest tests/`
5. **Submit a pull request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints for new functions
- Write unit tests for new features
- Update documentation as needed

## Troubleshooting

### Common Issues

1. **Twitter API Rate Limits**:
   - Check rate limit status
   - Implement exponential backoff
   - Monitor API usage

2. **GitHub API Limits**:
   - Use authenticated requests
   - Cache API responses
   - Implement retry logic

3. **Duplicate Tweets**:
   - Check state database
   - Verify tool comparison logic
   - Clear queue if needed

### Debug Mode

Run in debug mode for detailed logging:

```bash
export LOG_LEVEL=DEBUG
python src/main.py --debug
```

## Deployment Options

### 1. GitHub Actions (Recommended)
- **Pros**: Free, integrated, reliable
- **Cons**: Limited to 6-hour intervals
- **Best for**: Small to medium frequency

### 2. Cloud Functions
- **Pros**: Serverless, cost-effective
- **Cons**: Cold starts, limited execution time
- **Best for**: Event-driven execution

### 3. Container Platform
- **Pros**: Full control, continuous running
- **Cons**: Higher cost, maintenance overhead
- **Best for**: High-frequency monitoring

## Security Considerations

- Store API keys securely using secrets management
- Use least-privilege access for GitHub tokens
- Implement rate limiting and abuse prevention
- Monitor for unauthorized access attempts
- Regular security updates for dependencies

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/ajeetraina/kubetools-twitter-bot/issues)
- 💬 **Questions**: [GitHub Discussions](https://github.com/ajeetraina/kubetools-twitter-bot/discussions)
- 📧 **Contact**: [Ajeet Singh Raina](mailto:ajeetraina@gmail.com)

## Acknowledgments

- [Collabnix Community](https://collabnix.com) for maintaining kubetools
- [Kubetools Repository](https://github.com/collabnix/kubetools) for the awesome tool list
- Twitter Developer Platform for API access

---

**⭐ Star this repository if you find it useful!**

**🐦 Follow [@kubetools](https://x.com/kubetools) for the latest Kubernetes tool updates!**
