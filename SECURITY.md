# Security Policy

## Reporting a Vulnerability

We take the security of RAGSentinel seriously. If you have discovered a security vulnerability, we appreciate your help in disclosing it to us in a responsible manner.

### Please Do NOT

- Open a public GitHub issue for the vulnerability
- Exploit the vulnerability beyond what is necessary to demonstrate it
- Share the vulnerability details with others before it has been addressed

### Please DO

- Report the vulnerability by emailing **security@ragsentinel.dev** (or open a private [GitHub Security Advisory](https://github.com/H2110202/RAGSentinel/security/advisories/new))
- Include a clear description of the vulnerability
- Provide steps to reproduce the issue
- If possible, suggest a fix or mitigation

### Response Timeline

| Stage | Target Time |
|-------|-------------|
| Acknowledgment | Within 48 hours |
| Initial Assessment | Within 5 business days |
| Fix Development | Depends on severity |
| Disclosure | After fix is released |

### Known Security Considerations

- **Default admin credentials**: The initial `admin/admin123` account must be changed immediately after deployment
- **SECRET_KEY**: Must be changed from the default value in production
- **CORS**: Default configuration allows all origins (`*`); restrict this in production
- **SQLite**: Suitable for small-to-medium deployments; consider PostgreSQL for production scale
- **RAGFLOW_API_KEY**: Store securely and never commit to version control

### Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |
| < 1.0   | ❌ |
