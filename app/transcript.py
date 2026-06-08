"""
Transcript fetcher via youtube-transcript-api (1.x).
Falls back to auto-generated captions if manual ones are unavailable.

Note: youtube-transcript-api 1.x replaced the old classmethod API
(YouTubeTranscriptApi.get_transcript / list_transcripts) with an
instance-based one (YouTubeTranscriptApi().fetch / .list). The 0.6.x line
stopped working once YouTube moved transcript delivery to the innertube
API — the old timedtext requests now return empty bodies, which surfaced
as 404 "no captions available" for every video.
"""
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import WebshareProxyConfig

from app.config import settings

# Route transcript fetches through Webshare residential proxies. YouTube
# throttles datacenter IPs after a couple of requests (empty timedtext
# responses -> false "no captions" 404s), so the proxy is required for
# reliable captions, not just nice-to-have.
_api = YouTubeTranscriptApi(
    proxy_config=WebshareProxyConfig(
        proxy_username=settings.webshare_proxy_username,
        proxy_password=settings.webshare_proxy_password,
    )
)


def fetch_transcript(video_id: str, lang: str = "en") -> list[dict] | None:
    # Preferred: any transcript in the requested language, falling back to English.
    try:
        fetched = _api.fetch(video_id, languages=[lang, "en"])
        return fetched.to_raw_data()
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        pass
    except Exception:
        pass

    # Fallback: explicitly locate an auto-generated transcript.
    try:
        transcript_list = _api.list(video_id)
        t = transcript_list.find_generated_transcript([lang, "en"])
        return t.fetch().to_raw_data()
    except Exception:
        return None
