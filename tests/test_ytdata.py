"""Unit tests for the official YouTube Data API mapping."""
import os
os.environ.setdefault("RAPIDAPI_PROXY_SECRET", "test-secret")
os.environ.setdefault("WEBSHARE_PROXY_USERNAME", "testuser")
os.environ.setdefault("WEBSHARE_PROXY_PASSWORD", "testpass")

from app.ytdata import _map_item


def test_map_item_to_standard_video_shape():
    item = {
        "id": "vid123",
        "snippet": {
            "title": "Cool Video",
            "channelId": "UCabc",
            "channelTitle": "Cool Channel",
            "publishedAt": "2026-06-01T10:00:00Z",
            "thumbnails": {
                "default": {"url": "d.jpg", "width": 120, "height": 90},
                "high": {"url": "h.jpg", "width": 480, "height": 360},
            },
        },
        "statistics": {"viewCount": "123456"},
        "contentDetails": {"duration": "PT5M30S"},
    }
    v = _map_item(item)
    assert v["video_id"] == "vid123"
    assert v["title"] == "Cool Video"
    assert v["channel_id"] == "UCabc"
    assert v["channel_title"] == "Cool Channel"
    assert v["view_count"] == 123456            # parsed to int
    assert v["published_time"] == "2026-06-01T10:00:00Z"
    assert v["duration"] == "PT5M30S"
    assert v["thumbnail_url"] == "h.jpg"        # widest thumbnail chosen
    assert len(v["thumbnails"]) == 2


def test_map_item_missing_stats_view_count_is_none():
    item = {"id": "x", "snippet": {"title": "t", "thumbnails": {}}, "statistics": {}}
    v = _map_item(item)
    assert v["view_count"] is None
    assert v["thumbnail_url"] is None
