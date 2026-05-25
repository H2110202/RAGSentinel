# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-25

### Added
- Fine-grained 4-level permission system (View / Download / Upload / Manage)
- 4 permission target types (Company / Department / Individual / Project Group)
- Document-level permission override within knowledge bases
- RAGFlow API proxy with OpenAI-compatible chat completion endpoint
- Automatic RAGFlow dataset/document sync on KB creation and document upload
- DingTalk organization structure synchronization
- DingTalk QR code login support
- Multi-step approval workflow engine
- Agent permission gateway for bot-based access control
- Permission caching with configurable TTL (5 min default)
- Vue 3 + Element Plus single-page admin dashboard
- Docker Compose deployment configuration
- Health check endpoint with RAGFlow connectivity test
- Database initialization script with default admin account
- Apache License 2.0

### Security
- JWT (HS256) authentication
- Password hashing via passlib (sha256_crypt)
- CORS middleware configuration
- Environment variable based configuration (no hardcoded secrets)
