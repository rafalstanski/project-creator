"""Create a new Kotlin project directory from the bundled template files."""

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
PROJECTS_DIR = Path(__file__).resolve().parent / "projects"
TEMPLATE_FILES = ("build.gradle.kts",)


def create_project(name: str, templates_dir: Path = TEMPLATES_DIR, projects_dir: Path = PROJECTS_DIR) -> Path:
    """Create ``<projects_dir>/<name>`` and copy each template file into it.

    Args:
        name: project directory name.
        templates_dir: directory containing the template files.
        projects_dir: directory under which the project is created.

    Returns:
        The path of the created project directory.

    Raises:
        ValueError: if ``name`` is empty or not a safe single directory name.
        FileExistsError: if the project directory already exists.
        FileNotFoundError: if a template file is missing from ``templates_dir``.
        shutil.Error: if a template file cannot be copied.
    """
    if not name:
        raise ValueError("Project name must not be empty.")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Invalid project name: {name!r}")

    target = projects_dir / name
    if target.exists():
        raise FileExistsError(f"Project directory already exists: {target}")

    target.mkdir(parents=True)
    # If a copy fails, the target directory is intentionally left on disk
    # so the user can inspect and remove it manually.
    for template_file in TEMPLATE_FILES:
        shutil.copyfile(templates_dir / template_file, target / template_file)
    return target


def main() -> int:
    """Parse arguments, create the project, and print its path.

    Prompts for the project name if it is not provided via the CLI.

    Returns:
        0 on success, 1 on any error.
    """
    parser = argparse.ArgumentParser(description="Create a new Kotlin project from templates.")
    parser.add_argument("name", nargs="?", help="Project name (directory name).")
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

    try:
        project_dir = create_project(name)
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
