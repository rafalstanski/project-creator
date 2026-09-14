# AGENTS.md

## Project

Create a minimal Gradle + Kotlin + JUnit 5 project scaffold.
Input: project name + package name. Uses latest stable versions fetched from GitHub releases.

## Stack

- Python 3.14 (pyenv, pinned via `.python-version`) — **stdlib recommended**; external dependencies only if needed
- `uv` manages the environment (`.venv/`); run the tool with `uv run project-creator` or `./run.sh`
- A local `gradle` CLI (>= 8.2) must be on `PATH`; the minimum is required by the `gradle init --no-incubating` command
- No test framework, no CI; the build system (hatchling) provides the `project-creator` console script and packages `templates/` into the wheel

## Conventions

- Google-style docstrings on all public functions
- Type annotations everywhere
- Function ordering follows the Stepdown Rule (clean code): imports, constants, public API first, then private helpers in call order (callers above callees, related helpers grouped together), and the CLI section (private CLI helpers + `main()` + `__main__` guard) at the bottom
- Errors → stderr, success → stdout
- Explicit exception handling (`HTTPError`, `URLError`, `ValueError`, `JSONDecodeError`)
- Exception flow: business functions raise, they never catch-and-print. Only `main()` catches.
  - User-facing failures: wrap low-level exceptions in a domain exception (e.g. `ProjectCreationError`) with a user-readable message; use `raise ... from exc` to keep the chain.
  - `main()` runs the whole pipeline in one `try`, catches the general `Exception`, prints `Error: {exc}` to stderr, and returns 1.
  - Functions never return `None` to signal failure — raise instead, so callers don't `is None`-check.
- ruff is the project linter/formatter — always run `uv run ruff check --fix` and `uv run ruff format` after changes; implementation must pass both cleanly before finishing a task
- pyright is the type checker (strict mode, config in `pyrightconfig.json`) — always run `uv run pyright --warnings` after changes; must pass cleanly before finishing a task

## Run

```bash
uv run -m project_creator.fetch_versions kotlin
uv run -m project_creator.fetch_versions gradle
uv run -m project_creator.java_versions 2.4.10
./run.sh myapp com.sample.package  # (package is optional, default `com.example`; also: uv run project-creator)
uv tool install .                  # (global `project-creator` command; use --force to update)
```
## Modes

This program can be invoked in two modes:
* **tool mode**: after using `uv tool install .` in can be used as CLI tool.
* **dev mode**: directly from checkout directory by using `uv run project-creator`. 

## Directories

- `project_creator/` — the Python package (`__main__` for `python -m project_creator`).
- `templates/` — source template files copied into new projects; packaged into the wheel via hatchling `force-include`.
- `projects/` — generated project directories in dev mode (created at runtime); in tool mode projects are created in the current working directory.
- `.cache/` — runtime cache in dev mode (`java_versions.json`); gitignored. In tool mode the cache lives in `~/.cache/project-creator/`.

## Modules

All modules live in the `project_creator/` package.

### `project_creator/paths.py`

Resolves the runtime locations (templates, projects, cache) and detects the execution mode:

* Dev mode: projects are created in `projects/` and cached in `.cache/`.
* Tool mode: projects are created in the current working directory and cached in `~/.cache/project-creator/`
  (`%LOCALAPPDATA%/project-creator` on Windows).

### `project_creator/fetch_versions.py`

Fetches the newest stable Gradle and Kotlin versions from their GitHub releases (gradle/gradle, JetBrains/kotlin).

### `project_creator/java_versions.py`

Looks up the JVM versions for a given Kotlin version (provided by the caller, never fetched).
Result is cached in `java_versions.json` under the mode-dependent cache directory; a cache miss
downloads the matching `kotlin-compiler-<ver>.zip` from the Kotlin GitHub release and parses
the compiler's "Supported versions:" error message produced by an invalid `-jvm-target` flag.

### `project_creator/create.py`

Main module to create project scaffold; exposes the `project-creator` console script. General flow:

1. Validates name/package format
2. Fetches the newest Gradle/Kotlin/Java versions
3. Checks the directory is free and creates `<projects_dir>/<name>/`
4. Sets up the Gradle files using external `gradle` CLI tool
5. Creates basic project folders e.g.: `src/main/kotlin`
6. Populates project files from `templates` directory replacing placeholders e.g.: `{{PACKAGE_NAME}}`

## Rules

1. Update `AGENTS.md` after finishing each task (add to Modules, update any section if changes relate to it)
2. Match existing code conventions (docstrings, types, error-handling pattern).
3. Stdlib recommended — external dependencies only if needed

## Agent Delegation Rules

- **Static code analysis**: Always launch `.opencode/agents/code-cleaner.md` (or `@code-cleaner`) for code static analysis (to run `ruff`, `pyright`).