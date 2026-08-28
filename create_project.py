"""Create a new Kotlin project directory from the bundled template files."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from fetch_gradle_version import get_latest_gradle_version

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
PROJECTS_DIR = Path(__file__).resolve().parent / "projects"
TEMPLATE_FILES = ("build.gradle.kts",)
DEFAULT_PACKAGE_NAME = "com.example"
PACKAGE_NAME_PLACEHOLDER = "{{PACKAGE_NAME}}"
PACKAGE_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")
# Deliberately simplified: also accepts Kotlin hard keywords (``class``) and
# all-underscore (``_``) segments, which the Kotlin compiler would reject.
KOTLIN_SRC_DIR = Path("src/main/kotlin")
RESOURCES_DIR = Path("src/main/resources")


@dataclass
class ProjectArgs:
    """Resolved inputs describing the project to create."""

    name: str
    package_name: str
    gradle_version: str


def _validate_project_inputs(name: str, package_name: str) -> None:
    """Validate project name and package name format."""
    if not name:
        raise ValueError("Project name must not be empty.")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Invalid project name: {name!r}")
    if not PACKAGE_RE.fullmatch(package_name):
        raise ValueError(f"Invalid package name: {package_name!r}")


def _run_gradle_init(target: Path, name: str, gradle_version: str) -> None:
    """Run ``gradle init`` and ``gradle wrapper`` in ``target``."""
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
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["gradle", "wrapper", "--gradle-version", gradle_version],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    )


def _strip_generated_comments(target: Path) -> None:
    """Remove generated header comments from Gradle build files."""
    settings_file = target / "settings.gradle.kts"
    settings_file.write_text(
        re.sub(r"/\*.*?\*/\s*", "", settings_file.read_text(), count=1, flags=re.DOTALL)
    )
    properties_file = target / "gradle.properties"
    properties_file.write_text(
        "\n".join(
            line
            for line in properties_file.read_text().splitlines()
            if not line.lstrip().startswith("#")
        ).lstrip("\n")
    )


def _populate_project_files(
    target: Path, templates_dir: Path, package_name: str
) -> None:
    """Copy template files, create source layout dirs, and substitute placeholders."""
    # If a copy fails, the target directory is intentionally left on disk
    # so the user can inspect and remove it manually.
    for template_file in TEMPLATE_FILES:
        shutil.copyfile(templates_dir / template_file, target / template_file)
    package_dirs = package_name.split(".")
    package_dir = target / KOTLIN_SRC_DIR.joinpath(*package_dirs)
    package_dir.mkdir(parents=True)
    (target / RESOURCES_DIR).mkdir(parents=True)
    shutil.copyfile(templates_dir / "App.kt", package_dir / "App.kt")
    for file in (target / "build.gradle.kts", package_dir / "App.kt"):
        content = file.read_text()
        file.write_text(content.replace(PACKAGE_NAME_PLACEHOLDER, package_name))


def create_project(
    name: str,
    package_name: str,
    gradle_version: str,
    templates_dir: Path = TEMPLATES_DIR,
    projects_dir: Path = PROJECTS_DIR,
) -> Path:
    """Create ``<projects_dir>/<name>`` and populate it from the template files.

    Args:
        name: project directory name.
        package_name: dotted Kotlin package name used in sources, Gradle
            scripts, and directory layout.
        gradle_version: Gradle version passed to the ``gradle wrapper`` task.
        templates_dir: directory containing the template files.
        projects_dir: directory under which the project is created.

    Returns:
        The path of the created project directory.

    Raises:
        ValueError: if ``name`` or ``package_name`` is invalid.
        FileExistsError: if the project directory already exists.
        FileNotFoundError: if the ``gradle`` executable is not on ``PATH``,
            if a template file is missing from ``templates_dir``, or if a
            generated file is missing.
        subprocess.CalledProcessError: if a ``gradle`` command fails.
        shutil.Error: if a template file cannot be copied.
    """
    _validate_project_inputs(name, package_name)
    if shutil.which("gradle") is None:
        raise FileNotFoundError("gradle executable not found on PATH.")
    target = projects_dir / name
    if target.exists():
        raise FileExistsError(f"Project directory already exists: {target}")
    target.mkdir(parents=True)
    _run_gradle_init(target, name, gradle_version)
    _strip_generated_comments(target)
    _populate_project_files(target, templates_dir, package_name)
    return target


def _prompt_value(prompt: str, label: str) -> str | None:
    """Read a value from stdin, printing an error and returning ``None`` on EOF."""
    try:
        return input(prompt).strip()
    except EOFError:
        print(f"Error: no {label} provided.", file=sys.stderr)
        return None


def _fetch_gradle_version() -> str | None:
    """Fetch the newest Gradle version, printing an error and returning ``None``."""
    try:
        return get_latest_gradle_version()
    except urllib.error.HTTPError as exc:
        print(f"Error: HTTP {exc.code} while fetching Gradle version.", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"Error: network/timeout: {exc.reason}", file=sys.stderr)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Error: could not determine Gradle version: {exc}", file=sys.stderr)
    return None


def _create_project_or_none(project_args: ProjectArgs) -> Path | None:
    """Call ``create_project``, printing an error and returning ``None`` on failure."""
    try:
        return create_project(
            project_args.name, project_args.package_name, project_args.gradle_version
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
    except FileExistsError:
        print(f"Error: project '{project_args.name}' already exists.", file=sys.stderr)
    except FileNotFoundError as exc:
        print(f"Error: not found: {exc}", file=sys.stderr)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        print(f"Error: gradle command failed: {detail}", file=sys.stderr)
    except OSError as exc:
        print(f"Error: could not copy template files: {exc}", file=sys.stderr)
    return None


def _print_created_path(project_dir: Path) -> int:
    """Print ``project_dir`` relative to cwd (falling back to absolute)."""
    try:
        print(project_dir.relative_to(Path.cwd()))
    except ValueError:
        print(project_dir)
    return 0


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create a new Kotlin project from templates."
    )
    parser.add_argument("name", nargs="?", help="Project name (directory name).")
    parser.add_argument("package", nargs="?", help="Dotted Kotlin package name.")
    return parser.parse_args()


def _resolve_project_name(cli_args: argparse.Namespace) -> str | None:
    """Return the project name from the CLI, or read it from stdin."""
    if cli_args.name is None:
        return _prompt_value("Project name: ", "project name")
    return cli_args.name.strip()


def _resolve_package_name(cli_args: argparse.Namespace) -> str | None:
    """Return the package name, prompting or defaulting to ``DEFAULT_PACKAGE_NAME``."""
    if cli_args.package is None:
        package = _prompt_value(
            f"Package name [{DEFAULT_PACKAGE_NAME}]: ", "package name"
        )
    else:
        package = cli_args.package.strip()
    if package is None:
        return None
    if not package:
        return DEFAULT_PACKAGE_NAME
    return package


def _build_project_args(
    name: str, package_name: str, gradle_version: str
) -> ProjectArgs:
    """Bundle the resolved inputs into a ``ProjectArgs``."""
    return ProjectArgs(name, package_name, gradle_version)


def main() -> int:
    """Parse arguments, resolve inputs, fetch the Gradle version, and print the path.

    Prompts for the project name or the package name if they are not provided
    via the CLI; the package defaults to ``DEFAULT_PACKAGE_NAME`` when the
    prompt answer is empty.

    Returns:
        0 on success, 1 on any error.
    """
    cli_args = _parse_args()

    name = _resolve_project_name(cli_args)
    if name is None:
        return 1
    package_name = _resolve_package_name(cli_args)
    if package_name is None:
        return 1
    gradle_version = _fetch_gradle_version()
    if gradle_version is None:
        return 1

    project_dir = _create_project_or_none(
        _build_project_args(name, package_name, gradle_version)
    )
    if project_dir is None:
        return 1

    return _print_created_path(project_dir)


if __name__ == "__main__":
    raise SystemExit(main())
