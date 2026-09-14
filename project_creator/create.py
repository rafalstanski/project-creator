"""Create a new Kotlin project directory from the bundled template files."""

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from project_creator.fetch_versions import fetch_gradle_version, fetch_kotlin_version
from project_creator.java_versions import get_java_versions
from project_creator.paths import TEMPLATES_DIR, projects_dir

TEMPLATE_FILES = ("build.gradle.kts", ".gitignore")
DEFAULT_PACKAGE_NAME = "com.example"
PACKAGE_NAME_PLACEHOLDER = "{{PACKAGE_NAME}}"
KOTLIN_VERSION_PLACEHOLDER = "{{KOTLIN_VERSION}}"
JAVA_VERSION_PLACEHOLDER = "{{JAVA_VERSION}}"
JAVA_VERSIONS_PLACEHOLDER = "{{JAVA_VERSIONS}}"
PACKAGE_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")
# Deliberately simplified: also accepts Kotlin hard keywords (``class``) and
# all-underscore (``_``) segments, which the Kotlin compiler would reject.
KOTLIN_SRC_DIR = Path("src/main/kotlin")
RESOURCES_DIR = Path("src/main/resources")


class ProjectCreationError(Exception):
    """Any error while creating a project; ``str(exc)`` is user-facing."""


@dataclass
class ResolvedVersions:
    """The fetched toolchain versions used to build a project."""

    gradle_version: str
    kotlin_version: str
    java_version: str
    supported_java_versions: tuple[str, ...]


def create_project(name: str, package_name: str | None = None) -> Path:
    """Create the project directory ``<projects_dir>/<name>``: resolve versions,
    then build it.

    Resolves the project inputs (validating the name/package), fetches the
    newest Gradle/Kotlin/Java versions, and builds the project directory
    from the template files.

    Args:
        name: the project (directory) name.
        package_name: the dotted Kotlin package name; defaults to
            ``DEFAULT_PACKAGE_NAME`` when ``None`` or empty.

    Returns:
        The path of the created project directory.

    Raises:
        ValueError: if ``name`` or ``package_name`` is invalid.
        FileExistsError: if the project directory already exists.
        FileNotFoundError: if the ``gradle`` executable is not on ``PATH``.
        ProjectCreationError: if a ``gradle`` command fails, or if the
            template files cannot be copied or the project files read/written.
        VersionFetchError: if the Gradle or Kotlin version cannot be fetched.
        JavaVersionLookupError: if the Java versions cannot be determined.
    """
    package_name = _default_package_name(package_name)
    _validate_project_inputs(name, package_name)
    _log_project_creation(name, package_name)
    versions = _resolve_versions()
    return _build_project(name, package_name, versions, TEMPLATES_DIR, projects_dir())


def _default_package_name(package_name: str | None) -> str:
    """Return ``package_name``, or ``DEFAULT_PACKAGE_NAME`` if ``None`` or empty."""
    if not package_name:
        return DEFAULT_PACKAGE_NAME
    return package_name


def _validate_project_inputs(name: str, package_name: str) -> None:
    """Validate project name and package name format."""
    if not name:
        raise ValueError("Project name must not be empty.")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Invalid project name: {name!r}")
    if not PACKAGE_RE.fullmatch(package_name):
        raise ValueError(f"Invalid package name: {package_name!r}")


def _log_project_creation(name: str, package_name: str) -> None:
    """Print the opening line announcing the project about to be created."""
    _log(f"Creating project {name} (package {package_name}) ...")


def _resolve_versions() -> ResolvedVersions:
    """Fetch the newest Gradle/Kotlin versions and the matching Java versions.

    Prints a progress message before and after each of the version lookups.

    Raises:
        VersionFetchError: if the Gradle or Kotlin version cannot be fetched.
        JavaVersionLookupError: if the Java versions cannot be determined.
    """
    _log("Fetching newest Gradle version...")
    gradle_version = fetch_gradle_version()
    _log(f"Gradle version: {gradle_version}")
    _log("Fetching newest Kotlin version...")
    kotlin_version = fetch_kotlin_version()
    _log(f"Kotlin version: {kotlin_version}")
    _log(f"Looking up Java versions for Kotlin {kotlin_version}...")
    java_info = get_java_versions(kotlin_version)
    _log(
        f"Java version: {java_info.proposed}"
        f" (supported: {', '.join(java_info.supported)})"
    )
    return ResolvedVersions(
        gradle_version=gradle_version,
        kotlin_version=kotlin_version,
        java_version=java_info.proposed,
        supported_java_versions=java_info.supported,
    )


def _build_project(
    name: str,
    package_name: str,
    versions: ResolvedVersions,
    templates_dir: Path,
    projects_dir: Path,
) -> Path:
    """Create ``<projects_dir>/<name>`` and populate it from the template files.

    Assumes the inputs and versions are already resolved and validated.

    Args:
        name: the project (directory) name.
        package_name: the dotted Kotlin package name.
        versions: the resolved toolchain versions.
        templates_dir: directory containing the template files.
        projects_dir: directory under which the project is created.

    Returns:
        The path of the created project directory.

    Raises:
        FileExistsError: if the project directory already exists.
        FileNotFoundError: if the ``gradle`` executable is not on ``PATH``.
        ProjectCreationError: if a ``gradle`` command fails, or if the
            template files cannot be copied or the project files read/written.
    """
    project_directory = _create_project_directory(name, projects_dir)
    _log(f"Project directory created: {_relative_to_cwd(project_directory)}")
    _initialize_gradle(project_directory, name, versions)
    _populate_project_files(project_directory, templates_dir, package_name, versions)
    return project_directory


def _create_project_directory(name: str, projects_dir: Path) -> Path:
    """Create the project directory under ``projects_dir``.

    Raises:
        FileExistsError: if the project directory already exists.
    """
    project_directory = projects_dir / name
    if project_directory.exists():
        raise FileExistsError(f"Project directory already exists: {project_directory}")
    project_directory.mkdir(parents=True)
    return project_directory


def _initialize_gradle(
    project_directory: Path, name: str, versions: ResolvedVersions
) -> None:
    """Initialize Gradle in the project: check the CLI, run ``gradle init``,
    then strip the generated comments from the Gradle build files.

    Raises:
        FileNotFoundError: if the ``gradle`` executable is not on ``PATH``.
        ProjectCreationError: if a ``gradle`` command fails.
    """
    _require_gradle_executable()
    _run_gradle_init(project_directory, name, versions.gradle_version)
    _strip_generated_comments(project_directory)
    _log("gradle init and wrapper completed.")


def _require_gradle_executable() -> None:
    """Ensure the ``gradle`` executable is available on ``PATH``.

    Raises:
        FileNotFoundError: if the ``gradle`` executable is not on ``PATH``.
    """
    if shutil.which("gradle") is None:
        raise FileNotFoundError("gradle executable not found on PATH.")


def _run_gradle_init(project_directory: Path, name: str, gradle_version: str) -> None:
    """Run ``gradle init`` and ``gradle wrapper`` in ``project_directory``.

    Prints a progress message before each command.

    Raises:
        ProjectCreationError: if a ``gradle`` command fails.
    """
    try:
        _log("Running 'gradle init' ...")
        subprocess.run(
            [
                "gradle",
                "init",
                "--type",
                "basic",
                "--dsl",
                "kotlin",
                "--project-name",
                name,
                "--no-incubating",
            ],
            cwd=project_directory,
            check=True,
            capture_output=True,
            text=True,
        )
        _log("Running 'gradle wrapper' ...")
        subprocess.run(
            ["gradle", "wrapper", "--gradle-version", gradle_version],
            cwd=project_directory,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ProjectCreationError(f"gradle command failed: {detail}") from exc


def _strip_generated_comments(project_directory: Path) -> None:
    """Remove generated header comments from Gradle build files."""
    settings_file = project_directory / "settings.gradle.kts"
    settings_file.write_text(
        re.sub(r"/\*.*?\*/\s*", "", settings_file.read_text(), count=1, flags=re.DOTALL)
    )
    properties_file = project_directory / "gradle.properties"
    properties_file.write_text(
        "\n".join(
            line
            for line in properties_file.read_text().splitlines()
            if not line.lstrip().startswith("#")
        ).lstrip("\n")
    )


def _populate_project_files(
    project_directory: Path,
    templates_dir: Path,
    package_name: str,
    versions: ResolvedVersions,
) -> None:
    """Copy template files and substitute placeholders in ``project_directory``.

    Prints a progress message before and after the work.

    Raises:
        ProjectCreationError: if a template file cannot be copied or a project
            file cannot be read or written.
    """
    _log("Populating project files from templates ...")
    try:
        _copy_template_files(project_directory, templates_dir, package_name)
        _substitute_placeholders(project_directory, package_name, versions)
    except OSError as exc:
        raise ProjectCreationError(f"could not populate project files: {exc}") from exc
    _log("Project files populated.")


def _copy_template_files(
    project_directory: Path, templates_dir: Path, package_name: str
) -> None:
    """Copy template files into ``project_directory`` and create the source layout dirs.

    If a copy fails, the project directory is intentionally left on disk
    so the user can inspect and remove it manually.
    """
    for template_file in TEMPLATE_FILES:
        shutil.copyfile(
            templates_dir / template_file, project_directory / template_file
        )
    package_dir = project_directory / KOTLIN_SRC_DIR.joinpath(*package_name.split("."))
    package_dir.mkdir(parents=True)
    (project_directory / RESOURCES_DIR).mkdir(parents=True)
    shutil.copyfile(templates_dir / "App.kt", package_dir / "App.kt")


def _substitute_placeholders(
    project_directory: Path, package_name: str, versions: ResolvedVersions
) -> None:
    """Replace the template placeholders in the created project files."""
    package_dir = project_directory / KOTLIN_SRC_DIR.joinpath(*package_name.split("."))
    for file in (project_directory / "build.gradle.kts", package_dir / "App.kt"):
        content = file.read_text()
        content = content.replace(PACKAGE_NAME_PLACEHOLDER, package_name)
        file.write_text(content)
    build_file = project_directory / "build.gradle.kts"
    content = build_file.read_text()
    content = content.replace(KOTLIN_VERSION_PLACEHOLDER, versions.kotlin_version)
    content = content.replace(JAVA_VERSION_PLACEHOLDER, versions.java_version)
    content = content.replace(
        JAVA_VERSIONS_PLACEHOLDER, ", ".join(versions.supported_java_versions)
    )
    build_file.write_text(content)


def _relative_to_cwd(path: Path) -> Path:
    """Return ``path`` relative to cwd, falling back to the absolute path."""
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def _log(message: str) -> None:
    """Print an informational progress message to stdout."""
    print(message)


def _prompt_value(prompt: str, label: str) -> str:
    """Read a value from stdin, raising if no input is available."""
    try:
        return input(prompt).strip()
    except EOFError as exc:
        raise ProjectCreationError(f"no {label} provided.") from exc


def _resolve_project_name(cli_args: argparse.Namespace) -> str:
    """Return the project name from the CLI, or read it from stdin."""
    if cli_args.name is None:
        return _prompt_value("Project name: ", "project name")
    return cli_args.name.strip()


def _resolve_package_name(cli_args: argparse.Namespace) -> str:
    """Return the package name, prompting or defaulting to ``DEFAULT_PACKAGE_NAME``."""
    if cli_args.package is None:
        package = _prompt_value(
            f"Package name [{DEFAULT_PACKAGE_NAME}]: ", "package name"
        )
    else:
        package = cli_args.package.strip()
    if not package:
        return DEFAULT_PACKAGE_NAME
    return package


def _print_created_path(project_directory: Path) -> int:
    """Print the final success line with ``project_directory`` relative to cwd."""
    print(f"Project created: {_relative_to_cwd(project_directory)}")
    return 0


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create a new Kotlin project from templates."
    )
    parser.add_argument("name", nargs="?", help="Project name (directory name).")
    parser.add_argument("package", nargs="?", help="Dotted Kotlin package name.")
    return parser.parse_args()


def main() -> int:
    """Parse arguments, prompt for any missing inputs, create the project,
    and print the final success line.

    Prompts for the project name or the package name if they are not
    provided via the CLI; the package defaults to ``DEFAULT_PACKAGE_NAME``
    when the prompt answer is empty.

    Returns:
        0 on success, 1 on any error.
    """
    try:
        cli_args = _parse_args()
        name = _resolve_project_name(cli_args)
        package_name = _resolve_package_name(cli_args)
        project_directory = create_project(name, package_name)
        return _print_created_path(project_directory)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
