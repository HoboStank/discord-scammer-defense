# Getting Started Guide

This guide will help you set up your development environment and start contributing to the Discord Scammer Defense project.

## Prerequisites

### Required Software
- Git
- Node.js 16.x or later
- Python 3.8 or later
- Docker and Docker Compose
- A code editor (VS Code recommended)

### Discord Setup
1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot user for your application
3. Get your bot token
4. Enable required intents (Presence, Server Members, Message Content)

## Development Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/discord-scammer-defense.git
cd discord-scammer-defense
```

### 2. Environment Configuration
```bash
# Copy example environment files
cp bot/config/.env.example bot/config/.env
cp api/.env.example api/.env
cp dashboard/.env.example dashboard/.env

# Edit the .env files with your configuration
# Particularly, add your Discord bot token to bot/config/.env
```

### 3. Using Docker (Recommended)
```bash
# Build and start all services
docker-compose up --build

# Start specific services
docker-compose up bot api db

# View logs
docker-compose logs -f bot
```

### 4. Local Development Setup (Alternative)

#### Discord Bot (Node.js)
```bash
cd bot
npm install
npm run dev
```

#### API Server (Python)
```bash
cd api
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
flask run
```

#### Dashboard (React)
```bash
cd dashboard
npm install
npm start
```

## Project Structure

### Bot Structure
```
bot/
├── src/
│   ├── index.js           # Entry point
│   ├── commands/          # Bot commands
│   ├── events/           # Event handlers
│   └── utils/            # Utility functions
├── detection/            # Detection logic
└── config/              # Configuration files
```

### API Structure
```
api/
├── src/
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   └── services/        # Business logic
└── tests/              # API tests
```

### Dashboard Structure
```
dashboard/
├── src/
│   ├── components/      # React components
│   ├── pages/          # Page components
│   └── services/       # API services
└── public/            # Static assets
```

## Development Workflow

1. **Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes**
- Write code
- Add tests
- Update documentation

3. **Run Tests**
```bash
# Bot tests
cd bot && npm test

# API tests
cd api && python -m pytest

# Dashboard tests
cd dashboard && npm test
```

4. **Submit Changes**
```bash
git add .
git commit -m "Description of changes"
git push origin feature/your-feature-name
```

5. **Create Pull Request**
- Go to GitHub
- Create a new Pull Request
- Fill out the PR template
- Request review

## Common Tasks

### Adding a New Bot Command
1. Create command file in `bot/src/commands/`
2. Register command in command handler
3. Add tests in `bot/tests/commands/`
4. Update command documentation

### Adding an API Endpoint
1. Create route in `api/src/routes/`
2. Add controller logic
3. Create/update models if needed
4. Add tests in `api/tests/`
5. Update API documentation

### Adding a Dashboard Feature
1. Create components in `dashboard/src/components/`
2. Add page if needed
3. Update routes
4. Add tests
5. Update user documentation

## Troubleshooting

### Common Issues

1. **Bot Won't Connect**
- Check Discord token
- Verify intents are enabled
- Check network connectivity

2. **Database Connection Issues**
- Verify PostgreSQL is running
- Check connection string
- Ensure migrations are applied

3. **Build Failures**
- Check Node.js/Python versions
- Clear node_modules or venv
- Verify all dependencies are installed

### Getting Help

1. Check existing documentation
2. Search GitHub issues
3. Ask in the development Discord channel
4. Contact project maintainers

## Next Steps

1. Review the [Project Overview](../architecture/overview.md)
2. Check the [Development Roadmap](../roadmap/roadmap.md)
3. Read the [Contributing Guidelines](contributing.md)
4. Pick an issue to work on
5. Join the development Discord server