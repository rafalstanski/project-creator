"""Determine the JVM versions supported by a given Kotlin version."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

JAVA_VERSIONS_FILE = (
    Path(__file__).resolve().parents[1] / ".cache" / "java_versions.json"
)
KOTLIN_COMPILER_RELEASES_URL = (
    "https://github.com/JetBrains/kotlin/releases/download/"
    "v{kotlin_version}/kotlin-compiler-{kotlin_version}.zip"
)
DEFAULT_TIMEOUT = 10
USER_AGENT = "project-creator/0.1"
JAVA_VERSION_RE = re.compile(r"^\d+(\.\d+)?$")
JAVA_VERSION_TOKEN_RE = re.compile(r'version "([^"]+)"')
SUPPORTED_VERSIONS_RE = re.compile(r"supported versions:\s*(.+)", re.IGNORECASE)


class JavaVersionLookupError(Exception):
    """Any error while looking up Java versions; ``str(exc)`` is user-facing."""


@dataclass
class JavaVersionInfo:
    """Java version info: the proposed one and all supported ones."""

    proposed: str
    supported: tuple[str, ...]


def get_java_versions(
    kotlin_version: str, timeout: int = DEFAULT_TIMEOUT
) -> JavaVersionInfo:
    """Return the proposed and all supported JVM versions for ``kotlin_version``.

    The versions are taken from the ``java_versions.json`` cache if already
    stored there; otherwise they are fetched from the Kotlin compiler and
    cached. The proposed version is the one installed on this machine if
    supported, else the newest supported one.

    Args:
        kotlin_version: the Kotlin version to look up, e.g. ``2.4.10``.
        timeout: network timeout in seconds.

    Raises:
        JavaVersionLookupError: if the versions cannot be determined or the
            mapping file cannot be read, written, or is invalid.
    """
    try:
        versions = _load_mapping().get(kotlin_version)
        if versions is None:
            supported = _download_supported_versions(kotlin_version, timeout)
        else:
            supported = tuple(versions)
        installed = _detect_installed_java()
        proposed = _propose_version(installed, supported)
        return JavaVersionInfo(proposed=proposed, supported=supported)
    except urllib.error.HTTPError as exc:
        raise JavaVersionLookupError(
            f"HTTP {exc.code} while downloading the Kotlin {kotlin_version} compiler."
        ) from exc
    except urllib.error.URLError as exc:
        raise JavaVersionLookupError(f"network/timeout: {exc.reason}") from exc
    except (
        ValueError,
        json.JSONDecodeError,
        OSError,
        zipfile.BadZipFile,
    ) as exc:
        raise JavaVersionLookupError(
            f"Java version lookup for Kotlin {kotlin_version} failed: {exc}"
        ) from exc


def _detect_installed_java() -> str | None:
    """Return the major version of the ``java`` executable on ``PATH``.

    The version is normalized to compiler form (``21.0.11`` → ``"21"``,
    ``1.8.0_412`` → ``"1.8"``).

    Returns:
        The normalized major version, or ``None`` if java is unavailable or
        its version cannot be determined.
    """
    java_exe = shutil.which("java")
    if java_exe is None:
        return None
    completed = subprocess.run(
        [java_exe, "-version"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        return None
    raw_output = f"{completed.stderr or ''}\n{completed.stdout or ''}"
    match = JAVA_VERSION_TOKEN_RE.search(raw_output)
    if match is None:
        return None
    parts = match.group(1).split(".")
    major = parts[0]
    if major == "1" and len(parts) > 1:
        major = f"1.{parts[1]}"
    if not JAVA_VERSION_RE.fullmatch(major):
        return None
    return major


def _propose_version(installed: str | None, supported: tuple[str, ...]) -> str:
    """Return ``installed`` if it is supported, else the newest supported one,
    normalized to integer JVM toolchain form."""
    if installed is not None and installed in supported:
        return _to_toolchain_version(installed)
    return _to_toolchain_version(max(supported, key=_version_key))


def _to_toolchain_version(version: str) -> str:
    """Return ``version`` as an integer JVM toolchain value (``"1.8"`` → ``"8"``)."""
    if version.startswith("1."):
        return version.removeprefix("1.")
    return version


def _load_mapping() -> dict[str, list[str]]:
    """Return the kotlin-version → java-versions mapping from ``JAVA_VERSIONS_FILE``.

    An absent file yields an empty mapping.

    Raises:
        ValueError: if the file is present but does not hold a valid mapping.
    """
    try:
        entries: object = json.loads(JAVA_VERSIONS_FILE.read_text())
    except FileNotFoundError:
        return {}
    if not isinstance(entries, dict):
        raise ValueError(f"unexpected JSON mapping in {JAVA_VERSIONS_FILE}.")
    payload = cast("dict[str, object]", entries)
    mapping: dict[str, list[str]] = {}
    for kotlin_version, versions in payload.items():
        if not isinstance(versions, list) or not versions:
            raise ValueError(
                f"unexpected versions for {kotlin_version!r} in {JAVA_VERSIONS_FILE}."
            )
        supported = cast("list[str]", versions)
        if not all(_valid_java_version(version) for version in supported):
            raise ValueError(
                f"unexpected versions for {kotlin_version!r} in {JAVA_VERSIONS_FILE}."
            )
        mapping[kotlin_version] = supported
    return mapping


def _valid_java_version(version: object) -> bool:
    """Return whether ``version`` is a syntactically valid JVM version."""
    return type(version) is str and JAVA_VERSION_RE.fullmatch(version) is not None


def _save_mapping(kotlin_version: str, versions: tuple[str, ...]) -> None:
    """Merge ``versions`` under ``kotlin_version`` into ``JAVA_VERSIONS_FILE``."""
    mapping = _load_mapping()
    mapping[kotlin_version] = list(versions)
    JAVA_VERSIONS_FILE.write_text(json.dumps(mapping, indent=4, sort_keys=True) + "\n")


def _version_key(version: str) -> tuple[int, int]:
    """Return the version as a two-part numeric tuple, e.g. ``"21"`` → ``(21, 0)``."""
    major, dot, minor = version.partition(".")
    return int(major), int(minor) if dot else 0


def _download_supported_versions(kotlin_version: str, timeout: int) -> tuple[str, ...]:
    """Return the JVM versions supported by Kotlin ``kotlin_version``.

    The Kotlin compiler is downloaded, queried, and the result is cached in
    ``JAVA_VERSIONS_FILE``.

    Raises:
        urllib.error.HTTPError: if the download returns a non-2xx status.
        urllib.error.URLError: on network failure or timeout.
        OSError: if the archive or mapping file cannot be handled.
        ValueError: if the compiler output cannot be parsed.
        zipfile.BadZipFile: if the downloaded archive is not a valid ZIP.
    """
    with tempfile.TemporaryDirectory(prefix="kotlin-compiler-") as tmp_dir:
        kotlin_exe = _download_compiler(kotlin_version, Path(tmp_dir), timeout)
        supported = _query_supported_versions(kotlin_exe)
        _save_mapping(kotlin_version, supported)
    return supported


def _download_compiler(kotlin_version: str, tmp_dir: Path, timeout: int) -> Path:
    """Download the Kotlin ``kotlin_version`` compiler and extract ``kotlinc``.

    The platform-specific launcher is selected: ``kotlinc.bat`` on Windows,
    the POSIX ``kotlinc`` script elsewhere (made executable).

    Returns:
        The path of the extracted ``kotlinc`` launcher.

    Raises:
        urllib.error.HTTPError: if the download returns a non-2xx status.
        urllib.error.URLError: on network failure or timeout.
        OSError: if the archive cannot be written or extracted.
        ValueError: if the archive does not contain the expected layout.
        zipfile.BadZipFile: if the downloaded archive is not a valid ZIP.
    """
    zip_path = tmp_dir / f"kotlin-compiler-{kotlin_version}.zip"
    url = KOTLIN_COMPILER_RELEASES_URL.format(kotlin_version=kotlin_version)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    response = urllib.request.urlopen(request, timeout=timeout)
    with response, zip_path.open("wb") as zip_file:
        shutil.copyfileobj(response, zip_file)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(tmp_dir)
    bin_dir = tmp_dir / "kotlinc" / "bin"
    kotlin_exe_name = "kotlinc.bat" if _is_windows() else "kotlinc"
    kotlin_exe = bin_dir / kotlin_exe_name
    if not kotlin_exe.is_file():
        raise ValueError(f"compiler archive is missing kotlinc/bin/{kotlin_exe_name}.")
    if not _is_windows():
        kotlin_exe.chmod(0o755)
    return kotlin_exe


def _query_supported_versions(kotlin_exe: Path) -> tuple[str, ...]:
    """Return the JVM versions supported by ``kotlin_exe``, ascending.

    The compiler is forced to print its supported targets by passing an
    invalid ``-jvm-target`` flag and parsing the error message.

    Raises:
        ValueError: if the list of supported versions cannot be parsed.
    """
    completed = subprocess.run(
        [str(kotlin_exe), "-jvm-target", "foo"],
        capture_output=True,
        text=True,
        check=False,
    )
    raw_output = f"{completed.stderr or ''}\n{completed.stdout or ''}"
    match = SUPPORTED_VERSIONS_RE.search(raw_output)
    if match is None:
        raise ValueError("could not find the list of supported versions.")
    versions = sorted(
        {
            version.strip()
            for version in match.group(1).split(",")
            if version.strip() and JAVA_VERSION_RE.fullmatch(version.strip())
        },
        key=_version_key,
    )
    if not versions:
        raise ValueError("no supported versions parsed from kotlinc output.")
    return tuple(versions)


def _is_windows() -> bool:
    """Return whether the current platform is Windows."""
    return sys.platform == "win32"


def _print_result(java_info: JavaVersionInfo) -> None:
    """Print the proposed version and, on the second line, the supported ones."""
    print(java_info.proposed)
    print(", ".join(java_info.supported))


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Show the proposed and supported JVM versions for a Kotlin version."
    )
    parser.add_argument("kotlin_version", help="Kotlin version to look up.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Network timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    """Fetch the JVM versions for the given Kotlin version and print them.

    Prints the proposed version and, on the second line, all supported
    versions.

    Returns:
        0 on success, 1 on any error.
    """
    try:
        cli_args = _parse_args()
        java_info = get_java_versions(cli_args.kotlin_version, cli_args.timeout)
        _print_result(java_info)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
