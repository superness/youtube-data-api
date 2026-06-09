# Real-Time YouTube Data

**Live YouTube data — videos, channels, search, trending, transcripts, comments and community posts — from a single fast REST API. No YouTube API key, no OAuth, no quota juggling. Just call and get clean JSON.**

Real-Time YouTube Data gives you everything you'd scrape YouTube for, already parsed into predictable JSON. It is built on YouTube's own internal data layer (the same one that powers youtube.com and the mobile apps), routed through residential infrastructure for reliability, and cached so your calls stay fast. You get current view counts, fresh uploads, full transcripts, comment threads, and channel intelligence without ever touching Google Cloud, API keys, or the 10,000-unit/day Data API quota that kills most projects.

## What you can do

- **Search YouTube** for any query and get back real, relevance-ranked results with video IDs, titles, channels and view counts — with pagination tokens for deep result sets.
- **Pull full video metadata**: title, description, channel, view count, duration, publish date, keywords, category, live status and thumbnails.
- **Fetch transcripts / captions** for any video that has them — manual or auto-generated — as a clean `[{text, start, duration}]` array. No key required.
- **Get trending videos** by region, straight from YouTube's official most-popular chart.
- **Explore channels**: metadata, subscriber counts, recent uploads, playlists, community posts, and channel-scoped search.
- **Read comments** on videos and community posts, with author, like counts, pins and replies.
- **Discover related content** via suggested videos, search autocomplete, and the regional home feed.
- **Resolve streaming formats** (itags, resolutions, bitrates, audio quality) for a video.

## Endpoints

| Endpoint | What it returns |
|---|---|
| `GET /search?q=` | Relevance-ranked video results (`+ region`, `page_token`) |
| `GET /video?id=` | Full video metadata & statistics |
| `GET /captions?video_id=` | Transcript array `{text, start, duration}` (`+ lang`) |
| `GET /trending?region=` | Official most-popular chart by region |
| `GET /channel?id=` | Channel metadata, subscriber & video counts |
| `GET /channel/videos?id=` | Recent uploads (`+ page_token`) |
| `GET /channel/playlists?id=` | Channel playlists |
| `GET /channel/community?id=` | Channel community posts |
| `GET /channel/search?id=&q=` | Search within a channel |
| `GET /playlist?id=` | Playlist items |
| `GET /video/comments?video_id=` | Comment threads with author, likes, replies |
| `GET /video/streaming-data?video_id=` | Available stream formats & qualities |
| `GET /suggested?video_id=` | Related / suggested videos |
| `GET /autocomplete?q=` | Search suggestions for a partial query |
| `GET /home?region=` | Regional home feed |
| `GET /community/post?id=` | A single community post |
| `GET /community/post/comments?id=` | Comments on a community post |

All responses are flat, documented JSON with stable field names (`video_id`, `title`, `channel_id`, `view_count`, `published_time`, `duration`, `thumbnail_url`, …). Paginated endpoints return a `next_page_token` you pass straight back in.

## Why this API

- **No Google API key, no OAuth, no quota.** Skip the Cloud Console entirely. The Data API's per-day quota means a handful of search calls can exhaust a project; here, search, channel browsing and metadata don't burn any Google quota.
- **Transcripts that actually work.** Caption fetching is the #1 thing that breaks on DIY scrapers because YouTube throttles datacenter IPs after a few requests. This API runs captions through residential proxies and falls back from manual to auto-generated transcripts, so you get text back instead of a 429.
- **Reliability fallbacks built in.** Channel uploads try YouTube's RSS feed first (instant, rock-solid) and fall back to the internal browse API; trending uses the official chart. Defensive parsing means missing fields come back as `null`, never a 500.
- **Cached and fast.** Hot data (video metadata, captions) is cached up to 24h; volatile data (comments, trending) refreshes on a tight TTL — you get speed without staleness.

## Typical use cases

- Build a YouTube search or discovery feature without managing Google API keys.
- Generate transcripts for summarization, search indexing, subtitles, or LLM pipelines.
- Monitor channels and trending topics for media analytics and competitive research.
- Mine comments for sentiment, moderation, or audience research.
- Power content-recommendation widgets with suggested videos and autocomplete.

## Good to know

- **Search is relevance-ranked, not recency-ranked** (just like YouTube itself) — expect a healthy mix of fresh and evergreen results.
- **Captions exist only when YouTube has them.** Some videos have no transcript at all; those return a 404 by design.
- Data reflects YouTube's public surface at request time; metrics like view counts move continuously.
