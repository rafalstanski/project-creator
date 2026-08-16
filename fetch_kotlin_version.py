"""Fetch the newest stable Kotlin version from the official GitHub releases."""

import json
import sys
import urllib.error
import urllib.request

RELEASES_URL = "https://api.github.com/repos/JetBrains/kotlin/releases/latest"
DEFAULT_TIMEOUT = 10
USER_AGENT = "project-creator/0.1"


def get_latest_kotlin_version(timeout: int = DEFAULT_TIMEOUT) -> str:
    """Return the newest stable Kotlin version, e.g. ``2.4.10``.

    Raises:
        urllib.error.HTTPError: if the API returns a non-2xx status.
        urllib.error.URLError: on network failure or timeout.
        ValueError: if the response is missing/empty version.
    """
    request = urllib.request.Request(
        RELEASES_URL,
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


def main() -> int:
    try:
        version = get_latest_kotlin_version()
    except urllib.error.HTTPError as exc:
        print(f"Error: HTTP {exc.code} while fetching Kotlin version.", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Error: network/timeout: {exc.reason}", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Error: could not determine Kotlin version: {exc}", file=sys.stderr)
        return 1

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
