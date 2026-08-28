# AGENTS.md

## Project

Create a minimal Gradle + Kotlin + JUnit 5 project scaffold.
Input: project name + package name. Uses latest stable versions fetched from GitHub releases.

## Stack

- Python 3.14 (pyenv, pinned via `.python-version`) — **stdlib recommended**; external dependencies only if needed
- `uv` manages the environment (`.venv/`); run scripts with `uv run`
- A local `gradle` CLI (>= 8.2) must be on `PATH` for `create_project.py`; the minimum is required by the `gradle init --no-incubating` command
- No build system, no test framework, no CI

## Conventions

- Google-style docstrings on all public functions
- Type annotations everywhere
- Errors → stderr, success → stdout
- Entry point: `main() -> int` + `raise SystemExit(main())`
- Explicit exception handling (`HTTPError`, `URLError`, `ValueError`, `JSONDecodeError`)
- Module-level constants: `RELEASES_URL`, `DEFAULT_TIMEOUT`, `USER_AGENT`
- ruff is the project linter/formatter — always run `uv run ruff check --fix` and `uv run ruff format` after changes; implementation must pass both cleanly before finishing a task
- pyright is the type checker (strict mode, config in `pyrightconfig.json`) — always run `uv run pyright --warnings` after changes; must pass cleanly before finishing a task

## Run

```bash
uv run fetch_kotlin_version.py   # → 2.4.10
uv run fetch_gradle_version.py   # → 9.7.1
uv run create_project.py myapp   # → projects/myapp/ (optional `package` arg, default `com.example`)
uv run pyright --warnings        # → 0 errors, 0 warnings
```

## Directories

- `templates/` — source template files copied into new projects.
- `projects/` — generated project directories (created at runtime).

## Git

- `N` is the task number from the GitHub project.
- Branch: `N-description`
- Commit: `#N: Short description` — keep messages simple and short (one line, no elaboration)
- The `N` in the commit must match the `N` in the branch (e.g. branch `4-scaffold` → commit `#4: Scaffold project dir`).

## Modules

- `fetch_kotlin_version.py` — Kotlin version lookup
- `fetch_gradle_version.py` — Gradle version lookup
- `create_project.py` — Gradle + Kotlin scaffold generator

### `fetch_kotlin_version.py`

Fetches the newest stable Kotlin version from the JetBrains/kotlin GitHub releases.

- `get_latest_kotlin_version(timeout: int = DEFAULT_TIMEOUT) -> str` → e.g. `2.4.10`
- `main()` prints it to stdout

### `fetch_gradle_version.py`

Same, for Gradle (gradle/gradle releases).

- `get_latest_gradle_version(timeout: int = DEFAULT_TIMEOUT) -> str` → e.g. `8.14.2`
- `main()` prints it

### `create_project.py`

`create_project(name, package_name, gradle_version, templates_dir, projects_dir) -> Path`

- creates `<projects_dir>/<name>/`, requires `gradle` on `PATH`
- runs `gradle init --type basic --dsl kotlin --project-name <name> --no-incubating`
- runs `gradle wrapper --gradle-version <gradle_version>`
- strips generated comments from `settings.gradle.kts` + `gradle.properties`
- copies `build.gradle.kts` into project root
- creates `src/main/kotlin` + `src/main/resources`
- copies `App.kt` into the `<package_name>` dirs, replaces `{{PACKAGE_NAME}}` (default `com.example`)

`main()` flow:

- `_parse_args` (CLI)
- resolves name/package from CLI or stdin via `_resolve_project_name` / `_resolve_package_name` (prompting via `_prompt_value`, default `com.example`)
- `_fetch_gradle_version` (errors → `None`)
- packs into the `ProjectArgs` dataclass via `_build_project_args`
- creates via `_create_project_or_none(project_args)` (errors → `None`)
- prints the created path via `_print_created_path`

## Rules

1. Update `AGENTS.md` after finishing each task (add to Modules, update any section if changes relate to it)
2. Match existing code conventions (docstrings, types, error-handling pattern)
3. Stdlib recommended — external dependencies only if needed
4. Follow `#N:` commit and `N-` branch naming