"""
Official YouTube Data API v3 client.

Used only for endpoints the keyless InnerTube path can no longer serve — namely
trending, which YouTube retired in 2025 (the FEtrending browse feed now 400s).
The Data API's `videos.list?chart=mostPopular` returns current popular videos by
region at 1 quota unit per call.
"""
import requests
from app.config import settings

_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _map_item(item: dict) -> dict:
    """Map a Data API video resource to this service's standard video shape."""
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    thumbs_by_size = snippet.get("thumbnails", {})
    thumbs = list(thumbs_by_size.values())
    best = max(thumbs, key=lambda t: t.get("width", 0), default={})
    view_count = stats.get("viewCount")
    return {
        "video_id": item.get("id"),
        "title": snippet.get("title"),
        "channel_id": snippet.get("channelId"),
        "channel_title": snippet.get("channelTitle"),
        "view_count": int(view_count) if view_count and view_count.isdigit() else None,
        "published_time": snippet.get("publishedAt"),
        "duration": item.get("contentDetails", {}).get("duration"),
        "thumbnail_url": best.get("url"),
        "thumbnails": thumbs,
    }


def fetch_most_popular(region: str = "US", max_results: int = 25) -> list[dict]:
    """Return the most-popular videos for a region via the official Data API."""
    resp = requests.get(
        _VIDEOS_URL,
        params={
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": max_results,
            "key": settings.youtube_api_key,
        },
        timeout=settings.request_timeout,
    )
    resp.raise_for_status()
    return [_map_item(it) for it in resp.json().get("items", [])]
