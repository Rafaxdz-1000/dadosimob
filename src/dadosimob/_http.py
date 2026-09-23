"""Polite HTTP client with retries and a local download cache."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path

import requests

from . import __version__

log = logging.getLogger(__name__)

USER_AGENT = f"dadosimob/{__version__} (+https://github.com/Rafaxdz-1000/dadosimob)"
MAX_RETRIES = 3
BACKOFF_BASE = 2.0
RETRY_STATUS = {429, 500, 502, 503, 504}


def default_cache_dir() -> Path:
    """Cache folder. Override with the ``DADOSIMOB_CACHE`` environment variable."""
    env = os.environ.get("DADOSIMOB_CACHE")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "dadosimob"


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def get(url: str, *, sess: requests.Session | None = None, timeout: float = 120, **kw) -> requests.Response:
    """GET with exponential backoff on transient failures."""
    sess = sess or session()
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = sess.get(url, timeout=timeout, **kw)
            if resp.status_code in RETRY_STATUS:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in RETRY_STATUS:
                raise
            last_exc = exc
            wait = BACKOFF_BASE ** (attempt + 1)
            log.warning("Falha ao baixar %s (%s). Nova tentativa em %.0fs", url, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"Não foi possível baixar {url} após {MAX_RETRIES} tentativas") from last_exc


def download(url: str, *, cache_dir: Path | None = None, filename: str | None = None, force: bool = False) -> Path:
    """Download ``url`` into the cache and return the local path.

    Files are keyed by URL, so a new upstream file (new URL) is fetched again,
    while repeated calls reuse the cached copy.
    """
    cache_dir = Path(cache_dir) if cache_dir else default_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode()).hexdigest()[:10]
    name = filename or url.rstrip("/").rsplit("/", 1)[-1]
    target = cache_dir / f"{key}_{name}"
    if target.exists() and not force:
        log.info("Usando cache: %s", target)
        return target
    log.info("Baixando %s", url)
    resp = get(url, stream=True)
    tmp = target.with_suffix(target.suffix + ".part")
    with open(tmp, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            fh.write(chunk)
    tmp.replace(target)
    return target
