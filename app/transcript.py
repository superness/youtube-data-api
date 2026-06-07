"""
Transcript fetcher via youtube-transcript-api.
Falls back to auto-generated captions if manual ones are unavailable.
"""
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


def fetch_transcript(video_id: str, lang: str = "en") -> list[dict] | None:
    try:
        return YouTubeTranscriptApi.get_transcript(video_id, languages=[lang, "en"])
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        pass
    except Exception:
        pass

    # Try generated transcript in requested language or English
    try:
        tl = YouTubeTranscriptApi.list_transcripts(video_id)
        t = tl.find_generated_transcript([lang, "en"])
        return t.fetch()
    except Exception:
        return None
