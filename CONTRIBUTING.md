# Contributing to Discord Scammer Defense

First off, thank you for considering contributing to Discord Scammer Defense! It's people like you that make DSD such a great tool for protecting Discord communities.

## Ways to Contribute

### Financial Support
If you find this project useful and want to support its development:
- Click the "Sponsor" button at the top of the repository
- Support through PayPal: irchris5@gmail.com
- Share the project with others who might be interested in supporting

Your financial support helps:
- Maintain and improve the bot
- Add new features
- Cover hosting costs
- Support continuous development

### Code Contributions

1. Fork the Repository
2. Create a Branch
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Test thoroughly
5. Commit your changes
   ```bash
   git commit -m "Add detailed description of your changes"
   ```
6. Push to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
7. Open a Pull Request

### Development Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   cd bot
   pip install -r requirements.txt
   ```
3. Set up PostgreSQL database
4. Configure environment variables
5. Run the bot:
   ```bash
   python src/bot.py
   ```

## Contribution Guidelines

### Code Style
- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and small

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, etc.)
- Reference issue numbers when applicable

### Pull Requests
1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update the changelog
5. Link related issues

### Bug Reports
When filing an issue, make sure to answer these questions:
1. What version are you using?
2. What did you do?
3. What did you expect to see?
4. What did you see instead?

### Feature Requests
Feature requests are welcome! Please provide:
1. Clear use case
2. Expected behavior
3. Why this would be useful

## Community

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Report inappropriate behavior

### Communication
- Use GitHub Issues for bug reports and features
- Use Pull Requests for code changes
- Join our Discord server for discussions

## Project Structure
```
discord-scammer-defense/
├── bot/                    # Discord bot core
├── api/                    # API server
├── docs/                   # Documentation
└── tests/                  # Test suite
```

## Testing
1. Run unit tests:
   ```bash
   python -m pytest
   ```
2. Test bot commands
3. Check database interactions
4. Verify API endpoints

## Documentation
- Update README.md for major changes
- Add docstrings to functions
- Update API documentation
- Keep the wiki current

## Recognition
Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

## Questions?
- Check existing documentation
- Search closed issues
- Create a new issue
- Join our Discord server

Thank you for contributing to Discord Scammer Defense!