"""Create a new Kotlin project directory from the bundled template files."""

import argparse
import re
import shutil
import sys
from pathlib import Path

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


def create_project(
    name: str,
    package_name: str,
    templates_dir: Path = TEMPLATES_DIR,
    projects_dir: Path = PROJECTS_DIR,
) -> Path:
    """Create ``<projects_dir>/<name>`` and populate it from the template files.

    Copies ``build.gradle.kts`` into the project root, creates the standard
    source layout (``src/main/kotlin``, ``src/main/resources``) with the
    package directory for ``package_name``, copies ``App.kt`` into the
    package directory, and replaces the ``PACKAGE_NAME_PLACEHOLDER`` token
    with ``package_name`` in both generated files.

    Args:
        name: project directory name.
        package_name: dotted Kotlin package name used in sources, Gradle
            scripts, and directory layout.
        templates_dir: directory containing the template files.
        projects_dir: directory under which the project is created.

    Returns:
        The path of the created project directory.

    Raises:
        ValueError: if ``name`` or ``package_name`` is invalid.
        FileExistsError: if the project directory already exists.
        FileNotFoundError: if a template file is missing from ``templates_dir``.
        shutil.Error: if a template file cannot be copied.
    """
    if not name:
        raise ValueError("Project name must not be empty.")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Invalid project name: {name!r}")
    if not PACKAGE_RE.fullmatch(package_name):
        raise ValueError(f"Invalid package name: {package_name!r}")

    target = projects_dir / name
    if target.exists():
        raise FileExistsError(f"Project directory already exists: {target}")

    package_dirs = package_name.split(".")
    target.mkdir(parents=True)
    # If a copy fails, the target directory is intentionally left on disk
    # so the user can inspect and remove it manually.
    for template_file in TEMPLATE_FILES:
        shutil.copyfile(templates_dir / template_file, target / template_file)
    package_dir = target / KOTLIN_SRC_DIR.joinpath(*package_dirs)
    package_dir.mkdir(parents=True)
    (target / RESOURCES_DIR).mkdir(parents=True)
    shutil.copyfile(templates_dir / "App.kt", package_dir / "App.kt")
    for file in (target / "build.gradle.kts", package_dir / "App.kt"):
        content = file.read_text()
        file.write_text(content.replace(PACKAGE_NAME_PLACEHOLDER, package_name))
    return target


def main() -> int:
    """Parse arguments, create the project, and print its path.

    Prompts for the project name or the package name if they are not provided
    via the CLI; the package defaults to ``DEFAULT_PACKAGE_NAME`` when the
    prompt answer is empty.

    Returns:
        0 on success, 1 on any error.
    """
    parser = argparse.ArgumentParser(
        description="Create a new Kotlin project from templates."
    )
    parser.add_argument("name", nargs="?", help="Project name (directory name).")
    parser.add_argument("package", nargs="?", help="Dotted Kotlin package name.")
    args = parser.parse_args()

    name = args.name
    if name is None:
        try:
            name = input("Project name: ").strip()
        except EOFError:
            print("Error: no project name provided.", file=sys.stderr)
            return 1
    else:
        name = name.strip()

    package = args.package
    if package is None:
        try:
            package = input(f"Package name [{DEFAULT_PACKAGE_NAME}]: ").strip()
        except EOFError:
            print("Error: no package name provided.", file=sys.stderr)
            return 1
    else:
        package = package.strip()
    if not package:
        package = DEFAULT_PACKAGE_NAME

    try:
        project_dir = create_project(name, package)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileExistsError:
        print(f"Error: project '{name}' already exists.", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: could not copy template files: {exc}", file=sys.stderr)
        return 1

    try:
        print(project_dir.relative_to(Path.cwd()))
    except ValueError:
        print(project_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
