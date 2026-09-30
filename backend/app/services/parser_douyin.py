import re
from dataclasses import dataclass

import httpx


@dataclass
class VideoInfo:
    platform: str
    video_id: str
    title: str
    author: str
    cover_url: str
    duration: int
    download_url: str
    audio_url: str = ""
    is_dash: bool = False


MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
}


def _ensure_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def _unescape_json_url(url: str) -> str:
    url = url.replace("\\u002F", "/").replace("\\u0026", "&")
    url = url.replace("\\u003D", "=").replace("\\u003F", "?")
    url = url.replace("\\/", "/")
    return url


async def parse_douyin_video(url: str) -> VideoInfo:
    """
    Parse Douyin share link by extracting embedded data from the share page.
    """
    url = _ensure_url(url)

    async with httpx.AsyncClient(
        headers=MOBILE_HEADERS, follow_redirects=True, timeout=15.0
    ) as client:
        # Step 1: Visit homepage to get initial cookies
        await client.get("https://www.douyin.com/")

        # Step 2: Follow share link → iesdouyin.com/share/video/{id}
        response = await client.get(url)
        final_url = str(response.url)
        html = response.text

        # Step 3: Extract video ID
        video_id_match = re.search(r'/video/(\d+)', final_url)
        if not video_id_match:
            video_id_match = re.search(r'"aweme_id"\s*:\s*"(\d+)"', html)
        if not video_id_match:
            raise ValueError(f"无法从链接中提取视频ID，请确认链接是有效的抖音分享链接")

        video_id = video_id_match.group(1)

        # Step 4: Parse video info from HTML
        title = "无标题"
        author = "未知作者"
        cover_url = ""
        duration = 0
        download_url = ""

        # Title: try "desc" (video description), og:title, or page title
        desc_match = re.search(r'"desc"\s*:\s*"(.*?)"', html)
        if desc_match:
            title = desc_match.group(1)
        else:
            og_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="(.*?)"', html)
            if og_match:
                title = og_match.group(1)
            else:
                title_match = re.search(r'<title>(.*?)</title>', html)
                if title_match:
                    raw = title_match.group(1)
                    if "DOCTYPE" not in raw and len(raw) < 200:
                        title = raw.replace("抖音-记录美好生活", "").strip().rstrip("-–— ")

        # Author
        author_match = re.search(r'"nickname"\s*:\s*"(.*?)"', html)
        if author_match:
            author = author_match.group(1)

        # Duration: find all values, pick the one in milliseconds (> 1000)
        dur_matches = re.findall(r'"duration"\s*:\s*(\d+)', html)
        for dur_str in dur_matches:
            dur_val = int(dur_str)
            if dur_val > 1000:  # this is the real duration in milliseconds
                duration = dur_val // 1000
                break
        else:
            # Fallback: use the first match as-is
            if dur_matches:
                duration = int(dur_matches[0])

        # Cover: extract first URL from url_list array
        cover_match = re.search(r'"cover"[^}]+"url_list"\s*:\s*\[\s*"([^"]*)"', html)
        if not cover_match:
            cover_match = re.search(r'"origin_cover"[^}]+"url_list"\s*:\s*\[\s*"([^"]*)"', html)
        if cover_match:
            cover_url = _unescape_json_url(cover_match.group(1))

        # Video download URL: prefer download_addr (no watermark)
        dl_match = re.search(
            r'"download_addr"\s*:\s*\{[^}]+"url_list"\s*:\s*\[\s*"([^"]*)"',
            html
        )
        if dl_match:
            download_url = _unescape_json_url(dl_match.group(1))
        else:
            # Fallback: play_addr, replace playwm → play
            play_match = re.search(
                r'"play_addr"\s*:\s*\{[^}]+"url_list"\s*:\s*\[\s*"([^"]*)"',
                html
            )
            if play_match:
                download_url = _unescape_json_url(play_match.group(1))
                download_url = download_url.replace("playwm", "play")

        if not download_url:
            raise ValueError("无法获取无水印视频地址，视频可能已删除或设为私密")

        return VideoInfo(
            platform="douyin",
            video_id=video_id,
            title=title,
            author=author,
            cover_url=cover_url,
            duration=duration,
            download_url=download_url,
        )
