"""
Parse Innertube's deeply nested JSON responses into clean flat dicts.
Defensive: never raises on missing fields, always returns None for gaps.
"""
from typing import Any


def _get(d: Any, *keys, default=None) -> Any:
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        elif isinstance(d, list) and isinstance(k, int) and k < len(d):
            d = d[k]
        else:
            return default
        if d is None:
            return default
    return d if d is not None else default


def _text(obj: Any) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        if "simpleText" in obj:
            return obj["simpleText"]
        runs = obj.get("runs", [])
        if runs:
            return "".join(r.get("text", "") for r in runs) or None
    return None


def _int_from_text(s: Any) -> int | None:
    if s is None:
        return None
    try:
        cleaned = str(s).replace(",", "").split()[0]
        return int(cleaned)
    except (ValueError, IndexError, AttributeError):
        return None


def _best_thumbnail(thumbs: list) -> str | None:
    if not thumbs:
        return None
    best = max(thumbs, key=lambda t: t.get("width", 0) * t.get("height", 0))
    return best.get("url")


def _walk(obj: Any, key: str, results: list, depth: int = 0) -> None:
    """Recursively collect all dicts that have `key` as a direct child."""
    if depth > 20:
        return
    if isinstance(obj, dict):
        if key in obj:
            results.append(obj[key])
        for v in obj.values():
            _walk(v, key, results, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, key, results, depth + 1)


def _collect(data: dict, kind: str) -> list[dict]:
    results: list[dict] = []
    _walk(data, kind, results)
    return results


# ── Video ──────────────────────────────────────────────────────────────────────

def parse_video(data: dict) -> dict:
    vd = data.get("videoDetails", {})
    mf = _get(data, "microformat", "playerMicroformatRenderer") or {}
    thumbs = _get(vd, "thumbnail", "thumbnails") or []
    return {
        "video_id": vd.get("videoId"),
        "title": vd.get("title"),
        "description": vd.get("shortDescription"),
        "channel_id": vd.get("channelId"),
        "channel_title": vd.get("author"),
        "view_count": _int_from_text(vd.get("viewCount")),
        "duration_seconds": _int_from_text(vd.get("lengthSeconds")),
        "is_live": bool(vd.get("isLiveContent")),
        "keywords": vd.get("keywords") or [],
        "published_at": mf.get("publishDate"),
        "category": mf.get("category"),
        "is_family_safe": mf.get("isFamilySafe"),
        "thumbnail_url": _best_thumbnail(thumbs),
        "thumbnails": thumbs,
    }


# ── Video renderer (search / trending / suggested results) ─────────────────────

def _parse_video_renderer(vr: dict) -> dict | None:
    vid = vr.get("videoId")
    if not vid:
        return None
    thumbs = _get(vr, "thumbnail", "thumbnails") or []
    channel_runs = (
        _get(vr, "ownerText", "runs")
        or _get(vr, "shortBylineText", "runs")
        or []
    )
    channel_id = _get(channel_runs, 0, "navigationEndpoint", "browseEndpoint", "browseId")
    channel_title = channel_runs[0].get("text") if channel_runs else None
    return {
        "video_id": vid,
        "title": _text(vr.get("title")),
        "channel_id": channel_id,
        "channel_title": channel_title,
        "view_count": _int_from_text(_text(vr.get("viewCountText"))),
        "published_time": _text(vr.get("publishedTimeText")),
        "duration": _text(vr.get("lengthText")),
        "thumbnail_url": _best_thumbnail(thumbs),
        "thumbnails": thumbs,
    }


# ── Search ─────────────────────────────────────────────────────────────────────

def parse_search(data: dict) -> dict:
    vrs = _collect(data.get("contents", {}), "videoRenderer")
    videos = [r for vr in vrs if (r := _parse_video_renderer(vr))]

    cont = None
    conts = _collect(data, "continuationCommand")
    if conts:
        cont = conts[0].get("token")

    return {"results": videos, "next_page_token": cont}


# ── Trending ───────────────────────────────────────────────────────────────────

def parse_trending(data: dict) -> list[dict]:
    vrs = _collect(data.get("contents", {}), "videoRenderer")
    return [r for vr in vrs if (r := _parse_video_renderer(vr))]


# ── Channel ────────────────────────────────────────────────────────────────────

def parse_channel(data: dict) -> dict:
    header = (
        _get(data, "header", "c4TabbedHeaderRenderer")
        or _get(data, "header", "pageHeaderRenderer")
        or {}
    )
    meta = _get(data, "metadata", "channelMetadataRenderer") or {}
    avatar_thumbs = _get(header, "avatar", "thumbnails") or []
    banner_thumbs = _get(header, "banner", "thumbnails") or []
    return {
        "channel_id": header.get("channelId") or meta.get("channelId"),
        "title": header.get("title") or meta.get("title"),
        "description": meta.get("description"),
        "keywords": meta.get("keywords"),
        "subscriber_count_text": _text(header.get("subscriberCountText")),
        "videos_count_text": _text(header.get("videosCountText")),
        "avatar_url": _best_thumbnail(avatar_thumbs),
        "banner_url": _best_thumbnail(banner_thumbs),
        "canonical_url": meta.get("canonicalUrl"),
    }


# ── Channel videos tab ─────────────────────────────────────────────────────────

def parse_channel_videos(data: dict) -> dict:
    vrs = _collect(data.get("contents", {}), "richItemRenderer")
    items = []
    for rir in vrs:
        vr = _get(rir, "content", "videoRenderer")
        if vr:
            parsed = _parse_video_renderer(vr)
            if parsed:
                items.append(parsed)

    # fallback: direct videoRenderer scan
    if not items:
        direct = _collect(data.get("contents", {}), "videoRenderer")
        items = [r for vr in direct if (r := _parse_video_renderer(vr))]

    cont = None
    conts = _collect(data, "continuationCommand")
    if conts:
        cont = conts[0].get("token")

    return {"videos": items, "next_page_token": cont}


# ── Playlist ───────────────────────────────────────────────────────────────────

def parse_playlist(data: dict) -> dict:
    sidebar = _get(data, "sidebar", "playlistSidebarRenderer", "items") or []
    primary = next(
        (s.get("playlistSidebarPrimaryInfoRenderer", {}) for s in sidebar if "playlistSidebarPrimaryInfoRenderer" in s),
        {},
    )

    pvrs = _collect(data.get("contents", {}), "playlistVideoRenderer")
    items = []
    for pvr in pvrs:
        vid = pvr.get("videoId")
        if not vid:
            continue
        thumbs = _get(pvr, "thumbnail", "thumbnails") or []
        items.append({
            "video_id": vid,
            "title": _text(pvr.get("title")),
            "duration": _text(pvr.get("lengthText")),
            "channel_id": _get(pvr, "shortBylineText", "runs", 0, "navigationEndpoint", "browseEndpoint", "browseId"),
            "channel_title": _text(pvr.get("shortBylineText")),
            "thumbnail_url": _best_thumbnail(thumbs),
            "index": _int_from_text(_text(pvr.get("index"))),
        })

    cont = None
    conts = _collect(data, "continuationCommand")
    if conts:
        cont = conts[0].get("token")

    stats = primary.get("stats") or []
    return {
        "playlist_id": _get(primary, "navigationEndpoint", "watchEndpoint", "playlistId"),
        "title": _text(primary.get("title")),
        "video_count_text": _text(stats[0]) if stats else None,
        "videos": items,
        "next_page_token": cont,
    }


# ── Suggested / next ───────────────────────────────────────────────────────────

def parse_suggested(data: dict) -> list[dict]:
    vrs = _collect(data.get("contents", {}), "compactVideoRenderer")
    return [r for vr in vrs if (r := _parse_video_renderer(vr))]
