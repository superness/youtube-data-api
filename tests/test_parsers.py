"""Parser unit tests — no network calls, pure dict transformations."""
import os
os.environ.setdefault("RAPIDAPI_PROXY_SECRET", "test-secret")
os.environ.setdefault("WEBSHARE_PROXY_USERNAME", "testuser")
os.environ.setdefault("WEBSHARE_PROXY_PASSWORD", "testpass")

from app.parsers import (
    parse_video,
    parse_search,
    parse_channel,
    parse_trending,
    parse_playlist,
    parse_suggested,
    _text,
    _int_from_text,
    _best_thumbnail,
)


def test_text_simple():
    assert _text("hello") == "hello"
    assert _text({"simpleText": "world"}) == "world"
    assert _text({"runs": [{"text": "foo"}, {"text": "bar"}]}) == "foobar"
    assert _text(None) is None


def test_int_from_text():
    assert _int_from_text("1,234,567 views") == 1234567
    assert _int_from_text("42") == 42
    assert _int_from_text(None) is None
    assert _int_from_text("N/A") is None


def test_best_thumbnail():
    thumbs = [
        {"url": "small.jpg", "width": 120, "height": 90},
        {"url": "large.jpg", "width": 1280, "height": 720},
        {"url": "medium.jpg", "width": 640, "height": 480},
    ]
    assert _best_thumbnail(thumbs) == "large.jpg"
    assert _best_thumbnail([]) is None


def test_parse_video_full():
    data = {
        "videoDetails": {
            "videoId": "abc123",
            "title": "Test Video",
            "shortDescription": "A test",
            "channelId": "UCtest",
            "author": "Test Channel",
            "viewCount": "1234567",
            "lengthSeconds": "360",
            "isLiveContent": False,
            "keywords": ["python", "api"],
            "thumbnail": {"thumbnails": [{"url": "thumb.jpg", "width": 1280, "height": 720}]},
        },
        "microformat": {
            "playerMicroformatRenderer": {
                "publishDate": "2024-01-15",
                "category": "Science & Technology",
                "isFamilySafe": True,
            }
        },
    }
    result = parse_video(data)
    assert result["video_id"] == "abc123"
    assert result["title"] == "Test Video"
    assert result["view_count"] == 1234567
    assert result["duration_seconds"] == 360
    assert result["channel_id"] == "UCtest"
    assert result["published_at"] == "2024-01-15"
    assert result["thumbnail_url"] == "thumb.jpg"
    assert result["keywords"] == ["python", "api"]
    assert result["is_live"] is False


def test_parse_video_missing_fields():
    result = parse_video({})
    assert result["video_id"] is None
    assert result["view_count"] is None
    assert result["keywords"] == []
    assert result["thumbnails"] == []


def test_parse_search_empty():
    result = parse_search({})
    assert result["results"] == []
    assert result["next_page_token"] is None


def test_parse_search_with_results():
    data = {
        "contents": {
            "twoColumnSearchResultsRenderer": {
                "primaryContents": {
                    "sectionListRenderer": {
                        "contents": [{
                            "itemSectionRenderer": {
                                "contents": [{
                                    "videoRenderer": {
                                        "videoId": "vid1",
                                        "title": {"runs": [{"text": "My Video"}]},
                                        "ownerText": {"runs": [{
                                            "text": "My Channel",
                                            "navigationEndpoint": {
                                                "browseEndpoint": {"browseId": "UCchan1"}
                                            }
                                        }]},
                                        "viewCountText": {"simpleText": "5,000,000 views"},
                                        "publishedTimeText": {"simpleText": "1 year ago"},
                                        "lengthText": {"simpleText": "10:30"},
                                        "thumbnail": {"thumbnails": [{"url": "v1.jpg", "width": 320, "height": 180}]},
                                    }
                                }]
                            }
                        }]
                    }
                }
            }
        }
    }
    result = parse_search(data)
    assert len(result["results"]) == 1
    v = result["results"][0]
    assert v["video_id"] == "vid1"
    assert v["title"] == "My Video"
    assert v["channel_id"] == "UCchan1"
    assert v["channel_title"] == "My Channel"
    assert v["view_count"] == 5000000
    assert v["duration"] == "10:30"


def test_parse_channel_full():
    data = {
        "header": {
            "c4TabbedHeaderRenderer": {
                "channelId": "UCtest123",
                "title": "Great Channel",
                "subscriberCountText": {"simpleText": "1.23M subscribers"},
                "videosCountText": {"runs": [{"text": "456 videos"}]},
                "avatar": {"thumbnails": [{"url": "avatar.jpg", "width": 176, "height": 176}]},
                "banner": {"thumbnails": [{"url": "banner.jpg", "width": 2560, "height": 424}]},
            }
        },
        "metadata": {
            "channelMetadataRenderer": {
                "description": "A great channel",
                "keywords": "tech python coding",
                "canonicalUrl": "https://www.youtube.com/@greatchannel",
            }
        },
    }
    result = parse_channel(data)
    assert result["channel_id"] == "UCtest123"
    assert result["title"] == "Great Channel"
    assert result["subscriber_count_text"] == "1.23M subscribers"
    assert result["description"] == "A great channel"
    assert result["avatar_url"] == "avatar.jpg"
    assert result["banner_url"] == "banner.jpg"


def test_parse_trending_empty():
    assert parse_trending({}) == []


def test_parse_playlist_empty():
    result = parse_playlist({})
    assert result["videos"] == []
    assert result["next_page_token"] is None


def test_parse_suggested_empty():
    result = parse_suggested({})
    assert result == []
