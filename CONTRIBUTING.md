# Contributing to RAGSentinel

First off, thank you for considering contributing to RAGSentinel! It's people like you that make RAGSentinel such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (code snippets, screenshots)
- **Describe the behavior you observed** and what behavior you expected
- **Include your environment** (OS, Python version, RAGFlow version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a step-by-step description** of the suggested enhancement
- **Provide specific examples** to demonstrate the use case
- **Describe the current behavior** and explain the expected behavior
- **Explain why this enhancement would be useful**

### Pull Requests

1. **Fork** the repository
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and commit with clear messages
4. **Test your changes** thoroughly
5. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** against the `main` branch

### Development Setup

```bash
# Clone your fork
git clone https://github.com/H2110202/RAGSentinel.git
cd RAGSentinel

# Backend setup
cd backend
pip install -r requirements.txt
python run.py

# Frontend setup (in another terminal)
cd frontend
node server.js
```

### Coding Standards

- **Python**: Follow PEP 8 style guide
- **JavaScript/Vue**: Follow the existing code style in the project
- **Commits**: Use clear, descriptive commit messages
- **No comments in code** unless absolutely necessary for explaining "why" (not "what")

### Project Structure

```
RAGSentinel/
├── backend/
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── core/         # Config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   └── schemas/      # Pydantic schemas
│   ├── uploads/          # Uploaded documents
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── index.html        # Single-page Vue 3 app
│   └── server.js         # Static file server
├── ragflow/              # RAGFlow Docker config
├── docker-compose.yml
├── .env.example
└── README.md
```

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
