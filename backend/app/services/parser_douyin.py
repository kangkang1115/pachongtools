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
    duration: int  # seconds
    download_url: str  # video download URL
    audio_url: str = ""  # B站 DASH audio URL
    is_dash: bool = False  # whether ffmpeg merge is needed


DOUYIN_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "Referer": "https://www.douyin.com/",
}


async def parse_douyin_video(url: str) -> VideoInfo:
    """
    Parse a Douyin share link and return clean video info.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        # Step 1: Follow short link to get video ID
        response = await client.get(url, headers=DOUYIN_MOBILE_HEADERS)
        final_url = str(response.url)

        # Extract video_id from final URL
        video_id_match = re.search(r"/video/(\d+)", final_url)
        if video_id_match:
            video_id = video_id_match.group(1)
        else:
            # Try extracting from share page HTML
            video_id_match = re.search(r"video/(\d+)", response.text)
            if video_id_match:
                video_id = video_id_match.group(1)
            else:
                raise ValueError(f"无法从链接中提取视频ID: {final_url}")

        # Step 2: Call Douyin internal API
        api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}"
        api_response = await client.get(api_url, headers={
            **DOUYIN_MOBILE_HEADERS,
            "Accept": "application/json",
        })
        api_response.raise_for_status()
        data = api_response.json()

        if data.get("status_code") != 0 or not data.get("item_list"):
            raise ValueError("抖音API返回数据异常，可能链接已失效或需要更新解析策略")

        item = data["item_list"][0]

        # Step 3: Extract video info
        title = item.get("desc", "无标题")
        author_info = item.get("author", {})
        author = author_info.get("nickname", "未知作者")

        # Cover image
        cover = item.get("video", {}).get("cover", {})
        cover_url = cover.get("url_list", [""])[0] if cover else ""

        # Duration in milliseconds → seconds
        duration_ms = item.get("video", {}).get("duration", 0)
        duration = duration_ms // 1000

        # Get watermark-free video URL
        video_info = item.get("video", {})
        download_addr = video_info.get("download_addr", {})
        play_addr = video_info.get("play_addr", {})

        raw_url = ""
        if download_addr:
            url_list = download_addr.get("url_list", [])
            raw_url = url_list[0] if url_list else ""
        elif play_addr:
            url_list = play_addr.get("url_list", [])
            raw_url = url_list[0] if url_list else ""

        # Replace watermark marker
        download_url = raw_url.replace("playwm", "play").replace("watermark=1", "watermark=0")

        if not download_url:
            raise ValueError("无法获取无水印视频地址")

        return VideoInfo(
            platform="douyin",
            video_id=video_id,
            title=title,
            author=author,
            cover_url=cover_url,
            duration=duration,
            download_url=download_url,
        )
