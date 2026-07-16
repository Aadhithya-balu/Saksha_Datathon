# Security Policy

## Supported Versions

The Saksha project is currently under active development.

Only the latest version in the `main` branch receives security fixes and updates.

| Version | Supported |
|---------|-----------|
| Main (Latest) | ✅ Yes |
| Development Branches | ✅ Yes |
| Previous Releases | ❌ No |
| Archived Versions | ❌ No |

---

# Reporting a Security Vulnerability

The Saksha team takes security seriously and appreciates responsible disclosure of vulnerabilities.

If you discover a security issue, **please do not create a public GitHub Issue**.

Instead, report it privately to the project maintainer.

## Project Maintainer

**Aadhithya Balu**

Please include the following information in your report:

- Description of the vulnerability
- Steps to reproduce
- Affected component(s)
- Potential impact
- Suggested mitigation (if known)
- Screenshots or logs (if applicable)

---

# Response Timeline

Our goal is to respond according to the following timeline:

| Stage | Expected Time |
|--------|---------------|
| Initial acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Status update | Every 7 days |
| Security fix (if accepted) | As soon as possible depending on severity |

---

# Responsible Disclosure

Please follow responsible disclosure practices:

- Do not publicly disclose the vulnerability before it has been investigated.
- Do not exploit vulnerabilities beyond what is necessary to demonstrate the issue.
- Avoid accessing or modifying data that does not belong to you.
- Provide sufficient information to help reproduce the issue.

---

# Security Best Practices

Contributors should:

- Keep dependencies up to date.
- Never commit secrets, API keys, or credentials.
- Store sensitive configuration in environment variables.
- Follow the project's authentication and authorization mechanisms.
- Validate all user inputs.
- Write secure, production-quality code.
- Review AI-generated code before submitting Pull Requests.

---

# Secrets Management

Never commit:

- `.env` files
- Database credentials
- JWT secrets
- API keys
- OAuth credentials
- ML service credentials
- Cloud access keys

Always use GitHub Secrets or environment variables for sensitive information.

---

# AI-Assisted Development

AI-generated code must be reviewed for:

- Security vulnerabilities
- Hardcoded credentials
- Unsafe dependencies
- Injection risks
- Authentication bypasses
- Authorization issues
- Sensitive information leakage

All contributors remain responsible for the security of AI-assisted code.

---

# Scope

This policy applies to all components of the Saksha project, including:

- Frontend
- Backend
- REST APIs
- Authentication
- Database
- AI/ML Models
- MLOps Pipeline
- GitHub Actions
- Docker Configuration
- Infrastructure

---

# Acknowledgements

We appreciate responsible security researchers and contributors who help improve the security of Saksha through responsible disclosure.
