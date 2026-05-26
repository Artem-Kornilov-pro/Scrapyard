### Файл 3: `CONTRIBUTING.md`

```markdown
# Contributing to Scrapyard

## Branching Strategy

- `master` — stable, production-ready code
- `feature/*` — new features
- `fix/*` — bug fixes
- `docs/*` — documentation changes
- `test/*` — test additions
- `ci/*` — CI/CD changes

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `test:` — tests
- `ci:` — CI/CD
- `chore:` — maintenance
- `refactor:` — code refactoring
- `perf:` — performance improvements

## Pull Request Process

1. Create an Issue describing the change
2. Create a branch from `master`
3. Make your changes with conventional commits
4. Push and create a Pull Request
5. Ensure CI passes (tests, linting)
6. Request review
7. Merge to `master`

## Development Setup

```bash
git clone https://github.com/Artem-Kornilov-pro/scrapyard.git
cd scrapyard
cp .env.example .env
docker-compose up -d
```
```

---