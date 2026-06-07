"""
Raw Innertube API client. YouTube's internal API — no key, no quota.
POST-based JSON API that powers youtube.com and the mobile apps.
"""
import requests
from app.config import settings
from app.proxies import get_proxy_dict, get_random_user_agent

_BASE = "https://www.youtube.com/youtubei/v1"
_CLIENT_VERSION = "2.20240101.00.00"
_CLIENT_NAME = "WEB"


def _ctx(gl: str = "US", hl: str = "en") -> dict:
    return {
        "client": {
            "clientName": _CLIENT_NAME,
            "clientVersion": _CLIENT_VERSION,
            "hl": hl,
            "gl": gl,
            "userAgent": get_random_user_agent(),
        }
    }


def _post(endpoint: str, payload: dict, gl: str = "US", hl: str = "en") -> dict:
    body = {"context": _ctx(gl=gl, hl=hl), **payload}
    resp = requests.post(
        f"{_BASE}/{endpoint}",
        params={"prettyPrint": "false"},
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": _CLIENT_VERSION,
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/",
            "Accept-Language": f"{hl},{hl.split('-')[0]};q=0.9,en;q=0.8",
        },
        proxies=get_proxy_dict(),
        timeout=settings.request_timeout,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_video(video_id: str) -> dict:
    return _post("player", {
        "videoId": video_id,
        "playbackContext": {
            "contentPlaybackContext": {"html5Preference": "HTML5_PREF_WANTS"}
        },
    })


def fetch_search(
    query: str,
    gl: str = "US",
    page_token: str | None = None,
) -> dict:
    payload: dict = {"query": query}
    if page_token:
        payload["continuation"] = page_token
    return _post("search", payload, gl=gl)


def fetch_channel(channel_id: str) -> dict:
    return _post("browse", {"browseId": channel_id})


def fetch_channel_videos_tab(channel_id: str, page_token: str | None = None) -> dict:
    # params encodes the Videos tab in the channel page
    payload: dict = {
        "browseId": channel_id,
        "params": "EgZ2aWRlb3PyBgQKAjoA",
    }
    if page_token:
        payload["continuation"] = page_token
    return _post("browse", payload)


def fetch_trending(gl: str = "US") -> dict:
    return _post("browse", {"browseId": "FEtrending"}, gl=gl)


def fetch_playlist(playlist_id: str, page_token: str | None = None) -> dict:
    payload: dict = {"browseId": f"VL{playlist_id}"}
    if page_token:
        payload["continuation"] = page_token
    return _post("browse", payload)


def fetch_suggested(video_id: str) -> dict:
    return _post("next", {"videoId": video_id})
