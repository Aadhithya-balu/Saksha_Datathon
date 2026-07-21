# Contributing to Saksha

First off, thank you for contributing to **Saksha – Crime Intelligence & Analytical Platform**.

We appreciate every contribution that helps improve the platform. To keep development organized and maintain a stable codebase, please follow the guidelines below.

---

# Project Overview

Saksha is an AI-powered Crime Intelligence & Analytical Platform built for the Karnataka State Police.

Technology Stack

- FastAPI (Python 3.12)
- React + TypeScript + Vite
- Supabase PostgreSQL
- Neo4j Aura
- SQLAlchemy
- Zustand
- Recharts
- Docker
- MLflow
- GitHub Actions

---

# Development Workflow

All development must follow the GitHub Issue workflow.

```
Issue

↓

Create Feature Branch

↓

Implement Feature

↓

Run Tests

↓

Commit Changes

↓

Push Branch

↓

Create Pull Request

↓

Code Review

↓

Merge
```

Never commit directly to the `main` branch.

---

# Branch Naming

Use descriptive branch names.

Examples

```
feature/fir-management

feature/hotspot-model

feature/network-analysis

feature/ai-chat

fix/login-validation

fix/dashboard-api

docs/readme-update

refactor/auth-service
```

---

# Before You Start

Before working on any task:

- Read the project README.
- Read `agent_rules.md`.
- Read the assigned GitHub Issue carefully.
- Understand the project architecture.
- Pull the latest changes from the repository.

---

# Development Rules

Contributors must:

- Work only on the assigned GitHub Issue.
- Keep changes focused.
- Preserve existing functionality.
- Follow the existing project architecture.
- Maintain backward compatibility.
- Write clean and maintainable code.

Do NOT:

- Modify unrelated modules.
- Rewrite working functionality.
- Introduce unnecessary dependencies.
- Commit generated files unless required.
- Rename files or folders without approval.

---

# AI-Assisted Development

AI-assisted development is supported.

If using tools such as:

- ChatGPT
- GitHub Copilot
- Cursor
- Claude
- Gemini
- Windsurf
- Codex

You must:

- Follow `agent_rules.md`.
- Review all generated code.
- Test all generated code.
- Remove unnecessary AI-generated changes.
- Ensure generated code follows project standards.

The contributor remains fully responsible for all submitted code.

---

# Coding Standards

Backend

- Follow FastAPI best practices.
- Use type hints.
- Keep routes lightweight.
- Place business logic inside services.
- Use Pydantic schemas.
- Reuse existing utilities.

Frontend

- Use reusable React components.
- Keep components modular.
- Maintain existing UI patterns.
- Use TypeScript properly.
- Avoid duplicated logic.

Database

- Never modify schema without approval.
- Never commit credentials.
- Use migrations when applicable.

AI/ML

- Keep models independent.
- Reuse shared preprocessing.
- Follow the common model interface.
- Register trained models through the MLOps pipeline.

---

# Testing

Before submitting a Pull Request, verify:

Backend

```
pytest
```

Frontend

```
npm run build
```

Development

```
npm run dev:all
```

Ensure:

- No runtime errors.
- No build failures.
- No TypeScript errors.
- No React warnings.
- No broken API integrations.

---

# Pull Requests

Every Pull Request should:

- Solve a single issue.
- Have a clear title.
- Include a meaningful description.
- Pass all CI checks.
- Be reviewed before merging.

Pull Request template

```
## Summary

Brief description of the changes.

## Related Issue

Closes #

## Changes

- Added
- Updated
- Fixed

## Testing

- [ ] Backend tests
- [ ] Frontend build
- [ ] Manual testing

## Notes

Additional information if required.
```

---

# Commit Message Convention

Use meaningful commit messages.

Examples

```
feat: implement FIR management

feat: add hotspot prediction API

fix: resolve dashboard routing issue

fix: improve login validation

refactor: simplify analytics service

docs: update project README

test: add AI integration tests

chore: update dependencies
```

---

# Issue Ownership

Each GitHub Issue owns a specific feature.

Do not modify another issue's implementation unless absolutely necessary.

If shared files require changes:

- Keep modifications minimal.
- Preserve backward compatibility.
- Document the reason in the Pull Request.

---

# Code Review Checklist

Before requesting a review, ensure:

- [ ] Code follows project standards.
- [ ] Existing functionality is preserved.
- [ ] No unrelated files were modified.
- [ ] Tests pass.
- [ ] Documentation updated if necessary.
- [ ] No merge conflicts.
- [ ] Ready for production.

---

# Reporting Bugs

When reporting a bug, include:

- Steps to reproduce.
- Expected behavior.
- Actual behavior.
- Screenshots (if applicable).
- Browser/OS details.
- Relevant logs.

---

# Feature Requests

Feature requests should include:

- Problem statement.
- Proposed solution.
- Expected impact.
- Screenshots or mockups (if applicable).

---

# Security

Do not commit:

- `.env`
- API keys
- JWT secrets
- Database credentials
- Cloud credentials
- Personal information

See `SECURITY.md` for responsible disclosure guidelines.

---

# Community Standards

By participating in this project, you agree to follow the project's `CODE_OF_CONDUCT.md`.

Please be respectful, collaborative, and constructive in all interactions.

---

# Thank You

Thank you for contributing to Saksha.

Your contributions help build a modern AI-powered Crime Intelligence Platform for smarter policing and public safety.
