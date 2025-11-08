# Contributing Guide

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

## Commit Message Format

All commit messages must follow this format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

Must be one of the following:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (formatting, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

### Scope (optional)

The scope should be the name of the affected component:

- `api`: API endpoints
- `db`: Database models or migrations
- `middleware`: Middleware components
- `config`: Configuration changes
- `deps`: Dependency updates

### Subject

- Use imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize first letter
- No period (.) at the end
- Maximum 50 characters

### Examples

```bash
# Feature
feat(api): add user authentication endpoint

# Bug fix
fix(middleware): resolve request ID not propagating to logs

# Documentation
docs: update installation instructions

# Refactoring
refactor(db): simplify database connection logic

# Breaking change
feat(api)!: change response format to match RFC 7807

BREAKING CHANGE: The API response format has changed from custom format to RFC 7807 Problem Details.
```

## Using Commitizen (Recommended)

We recommend using Commitizen for interactive commit message creation:

### Install

```bash
uv sync --all-extras
```

### Create a commit

Instead of `git commit`, use:

```bash
cz commit
# or shorter
cz c
```

This will guide you through an interactive prompt:

```
? Select the type of change you are committing: (Use arrow keys)
 » feat      A new feature
   fix       A bug fix
   docs      Documentation only changes
   style     Changes that do not affect the meaning of the code
   refactor  A code change that neither fixes a bug nor adds a feature
   ...
```

### Bump version

Automatically bump version based on commits:

```bash
# Dry run (preview)
cz bump --dry-run

# Actual bump
cz bump

# Create changelog
cz changelog
```

## Pre-commit Hooks

Pre-commit hooks will automatically validate your commit message format.

### Setup

```bash
# Install hooks
pre-commit install --hook-type commit-msg

# Test commit message
echo "feat: add new feature" | pre-commit run conventional-pre-commit --hook-stage commit-msg
```

### What Gets Checked

1. **Code Quality**:
   - Ruff linting (auto-fix enabled)
   - Ruff formatting
   - mypy type checking

2. **Dependencies**:
   - uv.lock is up to date with pyproject.toml

3. **Commit Message**:
   - Follows Conventional Commits format
   - Valid type, scope, and subject

### Bypassing Hooks (Not Recommended)

If you absolutely need to skip hooks:

```bash
git commit --no-verify -m "message"
```

**Note**: This should only be used in exceptional circumstances. CI will still check your code.

## Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Make your changes

3. Run checks locally:
   ```bash
   # Format and lint
   uv run ruff check --fix .
   uv run ruff format .

   # Type check
   uv run mypy app

   # Update lock file if dependencies changed
   uv lock
   ```

4. Commit with commitizen:
   ```bash
   git add .
   cz commit
   ```

5. Or commit manually (must follow conventional commits):
   ```bash
   git commit -m "feat(api): add new endpoint for user management"
   ```

6. Push your changes:
   ```bash
   git push origin feat/your-feature-name
   ```

7. Create a Pull Request

## Commit Message Validation Examples

### ✅ Valid Commits

```bash
feat: add health check endpoint
fix(middleware): correct request ID generation
docs: update README with new installation steps
refactor(db)!: migrate to async SQLAlchemy 2.0
chore(deps): update FastAPI to 0.110.0
```

### ❌ Invalid Commits

```bash
# Missing type
"Add new feature"

# Invalid type
update: change configuration

# Capitalized subject
feat: Add new feature

# Period at end
feat: add new feature.

# Subject too long (>50 chars)
feat: add a really long subject that exceeds fifty characters in total length
```

## Version Bumping Rules

Commitizen automatically determines version bumps based on commit types:

- **BREAKING CHANGE** or `!` after type/scope → **MAJOR** version (1.0.0 → 2.0.0)
- **feat** → **MINOR** version (1.0.0 → 1.1.0)
- **fix** → **PATCH** version (1.0.0 → 1.0.1)
- Other types (docs, style, etc.) → No version bump

Example:

```bash
# Current version: 0.1.0

git commit -m "feat: add new API endpoint"
cz bump  # → 0.2.0

git commit -m "fix: resolve database connection issue"
cz bump  # → 0.2.1

git commit -m "feat!: change response format"
cz bump  # → 1.0.0 (major version bump)
```

## CI/CD Integration

GitHub Actions will automatically:

1. Validate all commit messages in pull requests
2. Run linting and type checking
3. Build Docker image
4. Check that uv.lock is up to date

See `.github/workflows/ci.yaml` for details.

## Questions?

If you have questions about the contribution process, please:

1. Check existing issues
2. Read the [Conventional Commits specification](https://www.conventionalcommits.org/)
3. Open a new issue for clarification