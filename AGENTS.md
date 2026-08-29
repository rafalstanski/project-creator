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
- Exception flow: business functions raise, they never catch-and-print. Only `main()` catches.
  - User-facing failures: wrap low-level exceptions in a domain exception (e.g. `ProjectCreationError`) with a user-readable message; use `raise ... from exc` to keep the chain.
  - `main()` runs the whole pipeline in one `try`, catches the general `Exception`, prints `Error: {exc}` to stderr, and returns 1.
  - Functions never return `None` to signal failure — raise instead, so callers don't `is None`-check.
- Module-level constants: `GRADLE_RELEASES_URL`, `KOTLIN_RELEASES_URL`, `DEFAULT_TIMEOUT`, `USER_AGENT`
- ruff is the project linter/formatter — always run `uv run ruff check --fix` and `uv run ruff format` after changes; implementation must pass both cleanly before finishing a task
- pyright is the type checker (strict mode, config in `pyrightconfig.json`) — always run `uv run pyright --warnings` after changes; must pass cleanly before finishing a task

## Run

```bash
uv run fetch_newest_versions.py kotlin   # → 2.4.10
uv run fetch_newest_versions.py gradle   # → 9.7.1
uv run create_project.py myapp   # → projects/myapp/ (optional `package` arg, default `com.example`)
uv run pyright --warnings        # → 0 errors, 0 warnings
```

## Directories

- `templates/` — source template files copied into new projects.
- `projects/` — generated project directories (created at runtime).

## Modules

- `fetch_newest_versions.py` — Gradle + Kotlin version lookup
- `create_project.py` — Gradle + Kotlin scaffold generator

### `fetch_newest_versions.py`

Fetches the newest stable Gradle and Kotlin versions from their GitHub releases
(gradle/gradle, JetBrains/kotlin).

- `fetch_gradle_version(timeout: int = DEFAULT_TIMEOUT) -> str` → e.g. `9.7.1`
- `fetch_kotlin_version(timeout: int = DEFAULT_TIMEOUT) -> str` → e.g. `2.4.10`
- `VersionFetchError(Exception)` — the module's domain exception; `str(exc)` is the user-facing error message
- `main()` — positional `which` arg (`gradle`/`kotlin`) + optional `--timeout`; prints the version to stdout

Bricks: `_fetch_newest_version` (shared HTTP/JSON/tag-parsing engine, raises `HTTPError`/`URLError`/`ValueError`) → `_fetch_tool_version` (wraps them in `VersionFetchError`) → public `fetch_*` functions.

### `create_project.py`

`create_project(project_args: ProjectArgs, templates_dir, projects_dir) -> Path`

Runs four lego bricks in order:

1. `_validate_project_inputs` — validates name/package format
2. `_create_project_directory` — checks the directory is free and creates `<projects_dir>/<name>/`
3. `_initialize_gradle` — `_require_gradle_executable`, `_run_gradle_init` (`gradle init --type basic --dsl kotlin --project-name <name> --no-incubating` + `gradle wrapper --gradle-version <gradle_version>`), `_strip_generated_comments` (from `settings.gradle.kts` + `gradle.properties`)
4. `_populate_project_files` — `_copy_template_files` (copies `build.gradle.kts` into project root, creates `src/main/kotlin` + `src/main/resources`, copies `App.kt` into the `<package_name>` dirs) + `_substitute_placeholders` (replaces `{{PACKAGE_NAME}}`, default `com.example`, and `{{KOTLIN_VERSION}}` with the fetched `kotlin_version`)

`main()` flow — the whole pipeline runs in one `try`; any `Exception` is
printed as `Error: <message>` to stderr and `main` returns 1:

- `_parse_args` (CLI)
- `_resolve_project_args` — resolves name/package from CLI or stdin via `_resolve_project_name` / `_resolve_package_name` (prompting via `_prompt_value`, default `com.example`), fetches the build-tool versions directly from `fetch_newest_versions` (`VersionFetchError` is caught by `main`), and packs everything into the `ProjectArgs` dataclass via `_build_project_args`
- `create_project(project_args)` (a failed `gradle` command is wrapped in `ProjectCreationError`)
- prints the created path via `_print_created_path`

`ProjectCreationError(Exception)` — the single domain exception; `str(exc)` is the user-facing error message.

## Rules

1. Update `AGENTS.md` after finishing each task (add to Modules, update any section if changes relate to it)
2. Match existing code conventions (docstrings, types, error-handling pattern)
3. Stdlib recommended — external dependencies only if needed