"""Fetch the newest stable Gradle and Kotlin versions from GitHub releases."""

import argparse
import json
import sys
import urllib.error
import urllib.request

GRADLE_RELEASES_URL = "https://api.github.com/repos/gradle/gradle/releases/latest"
KOTLIN_RELEASES_URL = "https://api.github.com/repos/JetBrains/kotlin/releases/latest"
DEFAULT_TIMEOUT = 10
USER_AGENT = "project-creator/0.1"
GRADLE = "gradle"
KOTLIN = "kotlin"
TOOL_NAMES = (GRADLE, KOTLIN)
RELEASES_URLS = {GRADLE: GRADLE_RELEASES_URL, KOTLIN: KOTLIN_RELEASES_URL}


class VersionFetchError(Exception):
    """Any error while fetching a version; ``str(exc)`` is user-facing."""


def _fetch_newest_version(releases_url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch the newest release version of a tool from the GitHub API.

    Raises:
        urllib.error.HTTPError: if the API returns a non-2xx status.
        urllib.error.URLError: on network failure or timeout.
        ValueError: if the response is missing/empty version.
    """
    request = urllib.request.Request(
        releases_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    tag_name = payload.get("tag_name")
    if not tag_name:
        raise ValueError(f"Unexpected GitHub release payload: {payload!r}")

    version = tag_name.lstrip("v")
    if not version:
        raise ValueError(f"Empty version derived from tag: {tag_name!r}")
    return version


def _fetch_tool_version(tool_name: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch a tool's version, converting low-level failures to ``VersionFetchError``.

    Args:
        tool_name: one of ``TOOL_NAMES``.
        timeout: network timeout in seconds.

    Raises:
        VersionFetchError: if the version cannot be fetched or determined.
    """
    try:
        return _fetch_newest_version(RELEASES_URLS[tool_name], timeout)
    except urllib.error.HTTPError as exc:
        raise VersionFetchError(
            f"HTTP {exc.code} while fetching {tool_name} version."
        ) from exc
    except urllib.error.URLError as exc:
        raise VersionFetchError(f"network/timeout: {exc.reason}") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise VersionFetchError(
            f"could not determine {tool_name} version: {exc}"
        ) from exc


def fetch_gradle_version(timeout: int = DEFAULT_TIMEOUT) -> str:
    """Return the newest stable Gradle version, e.g. ``9.7.1``.

    Raises:
        VersionFetchError: if the version cannot be fetched or determined.
    """
    return _fetch_tool_version(GRADLE, timeout)


def fetch_kotlin_version(timeout: int = DEFAULT_TIMEOUT) -> str:
    """Return the newest stable Kotlin version, e.g. ``2.4.10``.

    Raises:
        VersionFetchError: if the version cannot be fetched or determined.
    """
    return _fetch_tool_version(KOTLIN, timeout)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch the newest stable Gradle or Kotlin version."
    )
    parser.add_argument(
        "which", choices=TOOL_NAMES, help="Tool to fetch the version of."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Network timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    """Fetch the requested tool's version and print it to stdout.

    Returns:
        0 on success, 1 on any error.
    """
    try:
        cli_args = _parse_args()
        fetcher = (
            fetch_gradle_version if cli_args.which == GRADLE else fetch_kotlin_version
        )
        print(fetcher(cli_args.timeout))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
