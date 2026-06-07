"""
YouTube RSS feed reader — ultra-reliable, no auth, no quota.
Returns up to 15 most recent videos for a channel.
"""
import xml.etree.ElementTree as ET
import requests

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch_channel_rss(channel_id: str, timeout: int = 10) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    videos = []
    for entry in root.findall("atom:entry", _NS):
        vid_id = entry.findtext("yt:videoId", namespaces=_NS)
        if not vid_id:
            continue
        stats_el = entry.find("media:group/media:community/media:statistics", _NS)
        view_count = None
        if stats_el is not None:
            raw = stats_el.get("views")
            try:
                view_count = int(raw)
            except (TypeError, ValueError):
                pass
        rating_el = entry.find("media:group/media:community/media:starRating", _NS)
        videos.append({
            "video_id": vid_id,
            "title": entry.findtext("atom:title", namespaces=_NS),
            "published_at": entry.findtext("atom:published", namespaces=_NS),
            "updated_at": entry.findtext("atom:updated", namespaces=_NS),
            "view_count": view_count,
            "thumbnail_url": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
            "video_url": f"https://www.youtube.com/watch?v={vid_id}",
        })
    return videos
