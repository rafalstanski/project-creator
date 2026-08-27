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
python3 create_project.py myapp                # → projects/myapp/ (optional `package` arg, default `com.example`)
```

## Directories

- `templates/` — source template files copied into new projects.
- `projects/` — generated project directories (created at runtime).

## Git

- `N` is the task number from the GitHub project (matches the `#` column in Implemented).
- Branch: `N-description`
- Commit: `#N: Short description` — keep messages simple and short (one line, no elaboration)
- The `N` in the commit must match the `N` in the branch (e.g. branch `4-scaffold` → commit `#4: Scaffold project dir`).

## Implemented

| # | Task | File | Public API |
|---|------|------|------------|
| 1 | Fetch latest Kotlin version | `fetch_kotlin_version.py` | `get_latest_kotlin_version(timeout) -> str` |
| 3 | Fetch latest Gradle version | `fetch_gradle_version.py` | `get_latest_gradle_version(timeout) -> str` |
| 4 | Scaffold project dir from template | `create_project.py` | `create_project(name, package_name) -> Path` — copies `build.gradle.kts`, creates `src/main/kotlin` + `src/main/resources`, and `App.kt` into `<package_name>` dirs; replaces `{{PACKAGE_NAME}}` in both files (default `com.example`) |

## Rules

1. Update `AGENTS.md` after finishing each task (add to Implemented, update any section if changes relate to it)
2. Match existing code conventions (docstrings, types, error-handling pattern)
3. Stdlib only — no new dependencies without explicit approval
4. Follow `#N:` commit and `N-` branch naming