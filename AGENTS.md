# AGENTS.md

## Project

Create a minimal Gradle + Kotlin + JUnit 5 project scaffold.
Input: project name + package name. Uses latest stable versions fetched from GitHub releases.

## Stack

- Python 3.14 (pyenv) — **stdlib only**, no third-party dependencies
- No build system, no test framework, no CI

## Conventions

- Google-style docstrings on all public functions
- Type annotations everywhere
- Errors → stderr, success → stdout
- Entry point: `main() -> int` + `raise SystemExit(main())`
- Explicit exception handling (`HTTPError`, `URLError`, `ValueError`, `JSONDecodeError`)
- Module-level constants: `RELEASES_URL`, `DEFAULT_TIMEOUT`, `USER_AGENT`

## Run

```bash
python3 fetch_kotlin_version.py   # → 2.4.10
python3 fetch_gradle_version.py   # → 8.14.2
```
## Git

- Branch: `N-description`
- Commit: `#N: Short description`

## Implemented

| # | Task | File | Public API |
|---|------|------|------------|
| 1 | Fetch latest Kotlin version | `fetch_kotlin_version.py` | `get_latest_kotlin_version(timeout) -> str` |
| 3 | Fetch latest Gradle version | `fetch_gradle_version.py` | `get_latest_gradle_version(timeout) -> str` |

## Planned

- Fetch latest compatible Java SDK version (nice-to-have)
- Scaffold project: `gradle init` + template files (`build.gradle.kts`, `.gitignore`)
- Accept project name + package as CLI input

## Rules

1. Update `AGENTS.md` after finishing each task (add to Implemented, update any section if changes relate to it)
2. Match existing code conventions (docstrings, types, error-handling pattern)
3. Stdlib only — no new dependencies without explicit approval
4. Follow `#N:` commit and `N-` branch naming