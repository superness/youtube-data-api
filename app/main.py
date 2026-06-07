import hashlib
import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.cache import get_cached, set_cached
from app.innertube import (
    fetch_video,
    fetch_search,
    fetch_channel,
    fetch_channel_videos_tab,
    fetch_trending,
    fetch_playlist,
    fetch_suggested,
    fetch_autocomplete,
    fetch_home,
    fetch_video_comments,
    fetch_channel_playlists,
    fetch_channel_community,
)
from app.parsers import (
    parse_video,
    parse_search,
    parse_channel,
    parse_channel_videos,
    parse_trending,
    parse_playlist,
    parse_suggested,
    parse_home,
    parse_comments,
    parse_streaming_data,
    parse_channel_playlists,
    parse_channel_community,
)
from app.rss import fetch_channel_rss
from app.transcript import fetch_transcript

_redis: redis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    _redis.close()


app = FastAPI(title="YouTube Data API", lifespan=lifespan)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    if request.headers.get("X-RapidAPI-Proxy-Secret") != settings.rapidapi_proxy_secret:
        return JSONResponse(status_code=403, content={"error": "forbidden"})
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/video")
def video(id: str = Query(..., description="YouTube video ID, e.g. dQw4w9WgXcQ")):
    cached = get_cached(_redis, f"video:{id}")
    if cached:
        return cached
    try:
        result = parse_video(fetch_video(id))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    if not result.get("video_id"):
        raise HTTPException(404, "video not found")
    set_cached(_redis, f"video:{id}", result, ttl=86400)
    return result


@app.get("/channel")
def channel(id: str = Query(..., description="Channel ID starting with UC")):
    cached = get_cached(_redis, f"channel:{id}")
    if cached:
        return cached
    try:
        result = parse_channel(fetch_channel(id))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    if not result.get("channel_id"):
        raise HTTPException(404, "channel not found")
    set_cached(_redis, f"channel:{id}", result, ttl=21600)
    return result


@app.get("/channel/videos")
def channel_videos(
    id: str = Query(..., description="Channel ID"),
    page_token: str = Query(None, description="Pagination token from previous response"),
):
    if page_token:
        # Paginated: use Innertube browse
        cached = get_cached(_redis, f"chvid:{id}:{page_token}")
        if cached:
            return cached
        try:
            result = parse_channel_videos(fetch_channel_videos_tab(id, page_token=page_token))
        except Exception:
            raise HTTPException(502, "upstream unavailable")
        result["channel_id"] = id
        set_cached(_redis, f"chvid:{id}:{page_token}", result, ttl=3600)
        return result

    # First page: RSS (ultra-reliable, returns 15 recent videos instantly)
    cached = get_cached(_redis, f"chvid_rss:{id}")
    if cached:
        return cached
    try:
        videos = fetch_channel_rss(id)
    except Exception:
        # RSS failed — fall back to Innertube browse
        try:
            result = parse_channel_videos(fetch_channel_videos_tab(id))
            result["channel_id"] = id
            set_cached(_redis, f"chvid_rss:{id}", result, ttl=3600)
            return result
        except Exception:
            raise HTTPException(502, "upstream unavailable")
    result = {"channel_id": id, "videos": videos, "next_page_token": None}
    set_cached(_redis, f"chvid_rss:{id}", result, ttl=3600)
    return result


@app.get("/search")
def search(
    q: str = Query(..., description="Search query"),
    region: str = Query("US", description="ISO 3166-1 alpha-2 country code"),
    page_token: str = Query(None, description="Pagination token from previous response"),
):
    cache_key = "search:" + hashlib.sha256(
        f"{q}:{region}:{page_token}".encode()
    ).hexdigest()
    cached = get_cached(_redis, cache_key)
    if cached:
        return cached
    try:
        result = parse_search(fetch_search(q, gl=region, page_token=page_token))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    set_cached(_redis, cache_key, result, ttl=3600)
    return result


@app.get("/trending")
def trending(region: str = Query("US", description="ISO 3166-1 alpha-2 country code")):
    cached = get_cached(_redis, f"trending:{region}")
    if cached:
        return cached
    try:
        videos = parse_trending(fetch_trending(gl=region))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result = {"region": region, "videos": videos}
    set_cached(_redis, f"trending:{region}", result, ttl=1800)
    return result


@app.get("/playlist")
def playlist(
    id: str = Query(..., description="YouTube playlist ID"),
    page_token: str = Query(None, description="Pagination token from previous response"),
):
    cache_key = f"playlist:{id}:{page_token}"
    cached = get_cached(_redis, cache_key)
    if cached:
        return cached
    try:
        result = parse_playlist(fetch_playlist(id, page_token=page_token))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    set_cached(_redis, cache_key, result, ttl=7200)
    return result


@app.get("/captions")
def captions(
    video_id: str = Query(..., description="YouTube video ID"),
    lang: str = Query("en", description="BCP-47 language code, e.g. en, es, fr"),
):
    cached = get_cached(_redis, f"captions:{video_id}:{lang}")
    if cached:
        return cached
    result = fetch_transcript(video_id, lang)
    if result is None:
        raise HTTPException(404, "no captions available for this video")
    payload = {"video_id": video_id, "lang": lang, "transcript": result}
    set_cached(_redis, f"captions:{video_id}:{lang}", payload, ttl=86400)
    return payload


@app.get("/suggested")
def suggested(video_id: str = Query(..., description="YouTube video ID")):
    cached = get_cached(_redis, f"suggested:{video_id}")
    if cached:
        return cached
    try:
        videos = parse_suggested(fetch_suggested(video_id))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result = {"video_id": video_id, "suggested": videos}
    set_cached(_redis, f"suggested:{video_id}", result, ttl=3600)
    return result


@app.get("/autocomplete")
def autocomplete(
    q: str = Query(..., description="Partial search query"),
    lang: str = Query("en", description="BCP-47 language code"),
):
    cached = get_cached(_redis, f"autocomplete:{q}:{lang}")
    if cached:
        return cached
    try:
        suggestions = fetch_autocomplete(q, lang)
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result = {"query": q, "suggestions": suggestions}
    set_cached(_redis, f"autocomplete:{q}:{lang}", result, ttl=3600)
    return result


@app.get("/home")
def home(region: str = Query("US", description="ISO 3166-1 alpha-2 country code")):
    cached = get_cached(_redis, f"home:{region}")
    if cached:
        return cached
    try:
        videos = parse_home(fetch_home(gl=region))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result = {"region": region, "videos": videos}
    set_cached(_redis, f"home:{region}", result, ttl=1800)
    return result


@app.get("/video/comments")
def video_comments(
    video_id: str = Query(..., description="YouTube video ID"),
    page_token: str = Query(None, description="Pagination token from previous response"),
):
    cache_key = f"comments:{video_id}:{page_token}"
    cached = get_cached(_redis, cache_key)
    if cached:
        return cached
    try:
        result = parse_comments(fetch_video_comments(video_id, page_token))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result["video_id"] = video_id
    set_cached(_redis, cache_key, result, ttl=300)
    return result


@app.get("/video/streaming-data")
def video_streaming_data(video_id: str = Query(..., description="YouTube video ID")):
    try:
        result = parse_streaming_data(fetch_video(video_id))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    if not result.get("formats"):
        raise HTTPException(404, "no streaming data available")
    result["video_id"] = video_id
    return result


@app.get("/channel/playlists")
def channel_playlists(
    id: str = Query(..., description="Channel ID starting with UC"),
    page_token: str = Query(None, description="Pagination token from previous response"),
):
    cache_key = f"chplaylists:{id}:{page_token}"
    cached = get_cached(_redis, cache_key)
    if cached:
        return cached
    try:
        result = parse_channel_playlists(fetch_channel_playlists(id, page_token))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result["channel_id"] = id
    set_cached(_redis, cache_key, result, ttl=3600)
    return result


@app.get("/channel/community")
def channel_community(
    id: str = Query(..., description="Channel ID starting with UC"),
    page_token: str = Query(None, description="Pagination token from previous response"),
):
    cache_key = f"chcommunity:{id}:{page_token}"
    cached = get_cached(_redis, cache_key)
    if cached:
        return cached
    try:
        result = parse_channel_community(fetch_channel_community(id, page_token))
    except Exception:
        raise HTTPException(502, "upstream unavailable")
    result["channel_id"] = id
    set_cached(_redis, cache_key, result, ttl=1800)
    return result
