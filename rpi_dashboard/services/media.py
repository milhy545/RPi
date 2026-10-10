"""Media helpers for RPi-TV Dashboard.

YouTube cookie diagnostics, age checks, and lightweight preview metadata live
here so the player service can stay focused on mpv IPC.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from . import player


QUALITY = player.QUALITY
DQ = player.DQ


def _cookies_path() -> str:
    return str(Path(__file__).resolve().parents[2] / "yt-cookies.txt")


def norm(url: str) -> str:
    """Normalize URL by removing redundant slashes in path."""
    if not isinstance(url, str):
        return ""
    value = url.strip()
    try:
        parts = urlsplit(value)
    except Exception:
        return value
    if parts.scheme in ("http", "https"):
        return urlunsplit((parts.scheme, parts.netloc, os.path.normpath(parts.path) if parts.path else parts.path, parts.query, parts.fragment))
    return value


def yt_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    return player.yt_id(url) if isinstance(url, str) else None


def resolve(url: str, quality: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """Resolve a YouTube URL to a playable stream URL."""
    vid = yt_id(norm(url))
    if not vid:
        return norm(url), {"title": url[:50]}
    fmt = QUALITY.get(quality or DQ, QUALITY[DQ])
    try:
        import yt_dlp as youtube_dl
    except Exception as exc:
        return url, {"error": str(exc)}
    cookie_file = _cookies_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": fmt,
        "extractor_args": {"youtube": {"player_client": ["default", "android", "web"]}},
    }
    if os.path.exists(cookie_file):
        opts["cookiefile"] = cookie_file
    with youtube_dl.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://youtu.be/{vid}", download=False)
    stream_url = info.get("url")
    if not stream_url:
        formats = [f for f in (info.get("formats") or []) if f.get("url") and f.get("vcodec") != "none" and f.get("acodec") != "none"]
        formats.sort(key=lambda f: (f.get("height") or 0), reverse=True)
        if formats:
            stream_url = formats[0].get("url")
    if not stream_url:
        raise RuntimeError("No playable URL")
    meta = {"id": vid, "title": info.get("title", f"YT {vid}"), "h": info.get("height"), "dur": info.get("duration")}
    return stream_url, meta


def youtube_cookie_status() -> Dict[str, Any]:
    """Inspect local YouTube cookies without exposing values."""
    path = _cookies_path()
    info: Dict[str, Any] = {
        "ok": False,
        "path": path,
        "exists": os.path.exists(path),
        "cookie_count": 0,
        "age_seconds": None,
        "has_auth_cookies": False,
        "has_youtube_domain": False,
    }
    if not info["exists"]:
        return info
    st = os.stat(path)
    info["age_seconds"] = int(__import__("time").time() - st.st_mtime)
    info["size_bytes"] = st.st_size
    auth_names = {"SID", "HSID", "SSID", "APISID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID", "LOGIN_INFO"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                info["cookie_count"] += 1
                if "youtube.com" in line or "google.com" in line:
                    info["has_youtube_domain"] = True
                parts = line.rstrip("\n").split("\t")
                if parts and len(parts) >= 2 and parts[-2] in auth_names:
                    info["has_auth_cookies"] = True
    except Exception as exc:
        info["error"] = str(exc)
    info["ok"] = info["cookie_count"] > 0 and info["has_youtube_domain"]
    info["recommendation"] = "OK" if info["ok"] and info["has_auth_cookies"] else "Refresh BrowserOS YouTube cookies from a logged-in browser session."
    return info


def youtube_age_check(url: str) -> Dict[str, Any]:
    """Check whether a YouTube URL is playable with current cookies."""
    if not url:
        return {"ok": False, "error": "url required"}
    try:
        stream_url, meta = resolve(url, DQ)
        return {
            "ok": True,
            "title": meta.get("title"),
            "id": meta.get("id"),
            "duration": meta.get("dur"),
            "height": meta.get("h"),
            "cookies": youtube_cookie_status(),
            "playable_url": bool(stream_url),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:400], "cookies": youtube_cookie_status()}


def media_preview(url: str) -> Dict[str, Any]:
    """Return preview metadata for a media URL."""
    if not url:
        return {"ok": False, "error": "url required"}
    url = norm(url)
    vid = yt_id(url)
    if not vid:
        parts = urlsplit(url)
        title = os.path.basename(parts.path.rstrip("/")) or parts.netloc or url[:80]
        return {"ok": True, "type": "direct", "url": url, "title": title[:120], "thumbnail": "", "duration": None}
    try:
        import yt_dlp as youtube_dl
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": 8,
            "extractor_args": {"youtube": {"player_client": ["default", "android", "web"]}},
        }
        cookie_file = _cookies_path()
        if os.path.exists(cookie_file):
            opts["cookiefile"] = cookie_file
        with youtube_dl.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://youtu.be/{vid}", download=False)
        thumbs = info.get("thumbnails") or []
        thumb = info.get("thumbnail") or (thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg")
        return {
            "ok": True,
            "type": "youtube",
            "id": vid,
            "url": url,
            "title": info.get("title") or f"YouTube {vid}",
            "thumbnail": thumb,
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
        }
    except Exception as exc:
        return {"ok": False, "type": "youtube", "id": vid, "error": str(exc)[:400], "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}


__all__ = ["youtube_cookie_status", "youtube_age_check", "media_preview", "resolve", "yt_id", "norm"]
