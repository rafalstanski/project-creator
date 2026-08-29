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
- Module-level constants: `GRADLE_RELEASES_URL`, `KOTLIN_RELEASES_URL`, `JAVA_VERSIONS_FILE`, `KOTLIN_COMPILER_RELEASES_URL`, `DEFAULT_TIMEOUT`, `USER_AGENT`
- ruff is the project linter/formatter — always run `uv run ruff check --fix` and `uv run ruff format` after changes; implementation must pass both cleanly before finishing a task
- pyright is the type checker (strict mode, config in `pyrightconfig.json`) — always run `uv run pyright --warnings` after changes; must pass cleanly before finishing a task

## Run

```bash
uv run fetch_newest_versions.py kotlin   # → 2.4.10
uv run fetch_newest_versions.py gradle   # → 9.7.1
uv run supported_java_versions.py 2.4.10   # → proposed java version, then all supported ones
uv run create_project.py myapp   # → projects/myapp/ (optional `package` arg, default `com.example`)
uv run pyright --warnings        # → 0 errors, 0 warnings
```

## Directories

- `templates/` — source template files copied into new projects.
- `projects/` — generated project directories (created at runtime).
- `java_versions.json` — kotlin-version → java-versions mapping cache (created at runtime, kept in the repo).

## Modules

- `fetch_newest_versions.py` — Gradle + Kotlin version lookup
- `supported_java_versions.py` — supported + proposed JVM versions for a given Kotlin version
- `create_project.py` — Gradle + Kotlin scaffold generator

### `fetch_newest_versions.py`

Fetches the newest stable Gradle and Kotlin versions from their GitHub releases
(gradle/gradle, JetBrains/kotlin).

- `fetch_gradle_version(timeout: int = DEFAULT_TIMEOUT) -> str` → e.g. `9.7.1`
- `fetch_kotlin_version(timeout: int = DEFAULT_TIMEOUT) -> str` → e.g. `2.4.10`
- `VersionFetchError(Exception)` — the module's domain exception; `str(exc)` is the user-facing error message
- `main()` — positional `which` arg (`gradle`/`kotlin`) + optional `--timeout`; runs the whole pipeline in one `try`, prints the version to stdout; any `Exception` is printed as `Error: {exc}` to stderr and `main` returns 1

Bricks: `_fetch_newest_version` (shared HTTP/JSON/tag-parsing engine, raises `HTTPError`/`URLError`/`ValueError`) → `_fetch_tool_version` (wraps them in `VersionFetchError`) → public `fetch_*` functions.

### `supported_java_versions.py`

Looks up the JVM versions for a given Kotlin version (provided by the caller, never fetched).
Result is cached in `java_versions.json`; a cache miss downloads the matching
`kotlin-compiler-<ver>.zip` from the Kotlin GitHub release and parses the compiler's
"Supported versions:" error message produced by an invalid `-jvm-target` flag.

- `get_java_versions(kotlin_version: str, timeout: int = DEFAULT_TIMEOUT) -> JavaVersionInfo` → the proposed JVM version plus all supported ones
- `JavaVersionInfo` — dataclass: `proposed: str`, `supported: tuple[str, ...]`; the proposed version is the `java` one installed on `PATH` if supported, else the newest supported one
- `JavaVersionLookupError(Exception)` — the module's domain exception; `str(exc)` is the user-facing error message
- `main()` — positional `kotlin_version` arg + optional `--timeout`; prints the proposed version and then all supported versions comma-joined to stdout; any `Exception` is printed as `Error: {exc}` to stderr and `main` returns 1

Bricks: `_load_mapping` / `_save_mapping` (read/write the mapping file; unreadable/corrupt content raises `ValueError`) → `_download_compiler` (download + extract `kotlinc`) + `_query_supported_versions` (parse the compiler output, raises `ValueError`) + `_download_supported_versions` (cache-miss path: download, query, save) → `_detect_installed_java` (`java -version`, returns `None` if unavailable/unparsable) + `_propose_version`; `_download_supported_versions` failures are wrapped in `JavaVersionLookupError` by `get_java_versions`.

### `create_project.py`

`create_project(project_args: ProjectArgs, templates_dir, projects_dir) -> Path`

Runs four lego bricks in order:

1. `_validate_project_inputs` — validates name/package format
2. `_create_project_directory` — checks the directory is free and creates `<projects_dir>/<name>/`
3. `_initialize_gradle` — `_require_gradle_executable`, `_run_gradle_init` (`gradle init --type basic --dsl kotlin --project-name <name> --no-incubating` + `gradle wrapper --gradle-version <gradle_version>`), `_strip_generated_comments` (from `settings.gradle.kts` + `gradle.properties`)
4. `_populate_project_files` — `_copy_template_files` (copies `build.gradle.kts` into project root, creates `src/main/kotlin` + `src/main/resources`, copies `App.kt` into the `<package_name>` dirs) + `_substitute_placeholders` (replaces `{{PACKAGE_NAME}}`, default `com.example`, `{{KOTLIN_VERSION}}` with the fetched `kotlin_version`, `{{JAVA_VERSION}}` with the proposed java version, and `{{JAVA_VERSIONS}}` with the comma-joined supported java versions list)

`main()` flow — the whole pipeline runs in one `try`; any `Exception` is
printed as `Error: <message>` to stderr and `main` returns 1:

- `_parse_args` (CLI)
- `_resolve_project_args` — resolves name/package from CLI or stdin via `_resolve_project_name` / `_resolve_package_name` (prompting via `_prompt_value`, default `com.example`), fetches the Gradle/Kotlin versions directly from `fetch_newest_versions` and the matching Java versions from `supported_java_versions` (`VersionFetchError` / `JavaVersionLookupError` are caught by `main`), and packs everything into the `ProjectArgs` dataclass via `_build_project_args`
- `create_project(project_args)` (a failed `gradle` command or a file copy/read/write failure is wrapped in `ProjectCreationError`)
- prints the created path via `_print_created_path`

`ProjectCreationError(Exception)` — the single domain exception; `str(exc)` is the user-facing error message.

## Rules

1. Update `AGENTS.md` after finishing each task (add to Modules, update any section if changes relate to it)
2. Match existing code conventions (docstrings, types, error-handling pattern)
3. Stdlib recommended — external dependencies only if needed