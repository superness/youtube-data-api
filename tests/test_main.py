"""API endpoint tests — mock all network and Redis calls."""
import os
os.environ.setdefault("RAPIDAPI_PROXY_SECRET", "test-secret")
os.environ.setdefault("WEBSHARE_PROXY_USERNAME", "testuser")
os.environ.setdefault("WEBSHARE_PROXY_PASSWORD", "testpass")

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

_SECRET = "test-secret"
_HEADERS = {"X-RapidAPI-Proxy-Secret": _SECRET}

_MOCK_VIDEO = {
    "video_id": "abc123", "title": "Test", "description": "Desc",
    "channel_id": "UCtest", "channel_title": "TC", "view_count": 1000,
    "duration_seconds": 180, "is_live": False, "keywords": [],
    "published_at": "2024-01-01", "category": "Tech", "is_family_safe": True,
    "thumbnail_url": "t.jpg", "thumbnails": [],
}
_MOCK_CHANNEL = {
    "channel_id": "UCtest", "title": "TC", "description": "D",
    "keywords": None, "subscriber_count_text": "1M subs",
    "videos_count_text": "100 videos", "avatar_url": "a.jpg",
    "banner_url": "b.jpg", "canonical_url": None,
}
_MOCK_SEARCH = {"results": [], "next_page_token": None}


@pytest.fixture()
def mock_redis():
    r = MagicMock()
    r.get.return_value = None
    return r


@pytest.fixture()
def client(mock_redis):
    with patch("redis.Redis.from_url", return_value=mock_redis):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_blocks_no_secret(client):
    resp = client.get("/video?id=abc123")
    assert resp.status_code == 403


def test_video_endpoint(client):
    with patch("app.main.fetch_video", return_value={}), \
         patch("app.main.parse_video", return_value=_MOCK_VIDEO):
        resp = client.get("/video?id=abc123", headers=_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["video_id"] == "abc123"


def test_video_not_found(client):
    with patch("app.main.fetch_video", return_value={}), \
         patch("app.main.parse_video", return_value={"video_id": None}):
        resp = client.get("/video?id=missing", headers=_HEADERS)
    assert resp.status_code == 404


def test_channel_endpoint(client):
    with patch("app.main.fetch_channel", return_value={}), \
         patch("app.main.parse_channel", return_value=_MOCK_CHANNEL):
        resp = client.get("/channel?id=UCtest", headers=_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["channel_id"] == "UCtest"


def test_channel_not_found(client):
    with patch("app.main.fetch_channel", return_value={}), \
         patch("app.main.parse_channel", return_value={"channel_id": None}):
        resp = client.get("/channel?id=invalid", headers=_HEADERS)
    assert resp.status_code == 404


def test_channel_videos_rss(client):
    mock_videos = [{"video_id": "v1", "title": "T", "published_at": "2024-01-01",
                    "updated_at": "2024-01-02", "view_count": 500,
                    "thumbnail_url": "t.jpg", "video_url": "u"}]
    with patch("app.main.fetch_channel_rss", return_value=mock_videos):
        resp = client.get("/channel/videos?id=UCtest", headers=_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel_id"] == "UCtest"
    assert len(data["videos"]) == 1


def test_search_endpoint(client):
    with patch("app.main.fetch_search", return_value={}), \
         patch("app.main.parse_search", return_value=_MOCK_SEARCH):
        resp = client.get("/search?q=python", headers=_HEADERS)
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_trending_endpoint(client):
    with patch("app.main.fetch_trending", return_value={}), \
         patch("app.main.parse_trending", return_value=[]):
        resp = client.get("/trending?region=US", headers=_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["region"] == "US"


def test_captions_found(client):
    transcript = [{"text": "Hello", "start": 0.0, "duration": 1.5}]
    with patch("app.main.fetch_transcript", return_value=transcript):
        resp = client.get("/captions?video_id=abc123", headers=_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["video_id"] == "abc123"
    assert len(data["transcript"]) == 1


def test_captions_not_found(client):
    with patch("app.main.fetch_transcript", return_value=None):
        resp = client.get("/captions?video_id=abc123", headers=_HEADERS)
    assert resp.status_code == 404


def test_suggested_endpoint(client):
    with patch("app.main.fetch_suggested", return_value={}), \
         patch("app.main.parse_suggested", return_value=[]):
        resp = client.get("/suggested?video_id=abc123", headers=_HEADERS)
    assert resp.status_code == 200


def test_upstream_error_returns_502(client):
    with patch("app.main.fetch_video", side_effect=Exception("network error")):
        resp = client.get("/video?id=abc123", headers=_HEADERS)
    assert resp.status_code == 502


def test_playlist_endpoint(client):
    mock_playlist = {"playlist_id": "PL123", "title": "My List",
                     "video_count_text": "10", "videos": [], "next_page_token": None}
    with patch("app.main.fetch_playlist", return_value={}), \
         patch("app.main.parse_playlist", return_value=mock_playlist):
        resp = client.get("/playlist?id=PL123", headers=_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["playlist_id"] == "PL123"
