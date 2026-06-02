"""Update check against a static GitHub release asset.

We fetch a static ``version.json`` published as a release asset — **not**
the GitHub API. The API's unauthenticated limit is 60 req/hour per IP;
behind a shared office NAT that's 60/hour for the whole building, and a
bundled token is unacceptable. The static asset serves from the release
CDN without that limit.

Any failure (no network, blocked CDN, rate-limited, malformed manifest,
TLS interception) **fails silent** — logged for the developer, never
surfaced as a user-facing error. Beacon never self-replaces; the UI just
links to the releases page.

Configure the repo via BEACON_UPDATE_OWNER / BEACON_UPDATE_REPO env vars
(or edit the defaults below) before publishing releases.
"""

from __future__ import annotations

import os

import httpx
from packaging.version import InvalidVersion, parse

from engine.logging_setup import get_logger
from engine.version import __version__

log = get_logger()

_OWNER = os.environ.get("BEACON_UPDATE_OWNER", "your-org")
_REPO = os.environ.get("BEACON_UPDATE_REPO", "luxafor-flag-controller")

_MANIFEST_URL = (
    f"https://github.com/{_OWNER}/{_REPO}/releases/latest/download/version.json"
)
_RELEASES_URL = f"https://github.com/{_OWNER}/{_REPO}/releases"


def check() -> dict | None:
    """Return ``{version, url}`` if a newer release exists, else None.

    Never raises — all failures return None and are logged at debug.
    """
    try:
        resp = httpx.get(_MANIFEST_URL, timeout=8.0, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        remote = str(data["version"])
    except Exception as e:  # network, JSON, key, TLS — all swallowed
        log.debug("update check failed (silent): %s: %s", type(e).__name__, e)
        return None

    try:
        if parse(remote) > parse(__version__):
            return {"version": remote, "url": _RELEASES_URL}
    except InvalidVersion as e:
        log.debug("update check: bad version string %r: %s", remote, e)
        return None
    return None
