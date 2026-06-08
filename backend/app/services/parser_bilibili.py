import re
import httpx

from .parser_douyin import VideoInfo

BILIBILI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


async def parse_bilibili_video(url: str) -> VideoInfo:
    """
    Parse a Bilibili video URL and return DASH stream info.
    """
    # Step 1: Extract BV number or aid
    bv_match = re.search(r"BV[a-zA-Z0-9]{10}", url)
    aid_match = re.search(r"av(\d+)", url, re.IGNORECASE)

    if bv_match:
        bvid = bv_match.group(0)
        video_id = bvid
    elif aid_match:
        aid = aid_match.group(1)
        video_id = f"av{aid}"
    else:
        raise ValueError("无法从链接中提取 B站 视频ID")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get video info
        if bv_match:
            info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        else:
            info_url = f"https://api.bilibili.com/x/web-interface/view?aid={aid}"

        info_resp = await client.get(info_url, headers=BILIBILI_HEADERS)
        info_resp.raise_for_status()
        info_data = info_resp.json()

        if info_data.get("code") != 0:
            raise ValueError(f"B站API返回错误: {info_data.get('message', '未知错误')}")

        video_data = info_data["data"]
        title = video_data.get("title", "无标题")
        author = video_data.get("owner", {}).get("name", "未知作者")
        cover_url = video_data.get("pic", "")
        duration = video_data.get("duration", 0)

        # Get cid
        cid_list = video_data.get("pages", [])
        if not cid_list:
            raise ValueError("无法获取视频分P信息")
        cid = cid_list[0]["cid"]

        # Get play URL (DASH format)
        if bv_match:
            play_url = (
                f"https://api.bilibili.com/x/player/wbi/playurl"
                f"?bvid={bvid}&cid={cid}&fnval=4048&fnver=0&fourk=1"
            )
        else:
            play_url = (
                f"https://api.bilibili.com/x/player/wbi/playurl"
                f"?aid={aid}&cid={cid}&fnval=4048&fnver=0&fourk=1"
            )

        play_headers = {**BILIBILI_HEADERS, "Referer": f"https://www.bilibili.com/video/{video_id}"}
        play_resp = await client.get(play_url, headers=play_headers)
        play_resp.raise_for_status()
        play_data = play_resp.json()

        if play_data.get("code") != 0:
            # Fallback: try without fnval
            if bv_match:
                fallback_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}"
            else:
                fallback_url = f"https://api.bilibili.com/x/player/playurl?aid={aid}&cid={cid}"
            play_resp = await client.get(fallback_url, headers=play_headers)
            play_resp.raise_for_status()
            play_data = play_resp.json()

        dash_info = play_data.get("data", {})

        # Extract best DASH streams
        if "dash" in dash_info:
            dash = dash_info["dash"]
            video_streams = dash.get("video", [])
            audio_streams = dash.get("audio", [])

            if video_streams and audio_streams:
                best_video = video_streams[0]
                best_audio = audio_streams[0]
                return VideoInfo(
                    platform="bilibili",
                    video_id=video_id,
                    title=title,
                    author=author,
                    cover_url=cover_url,
                    duration=duration,
                    download_url=best_video.get("base_url", "") or best_video.get("baseUrl", ""),
                    audio_url=best_audio.get("base_url", "") or best_audio.get("baseUrl", ""),
                    is_dash=True,
                )
            else:
                raise ValueError("无法获取B站视频DASH流地址")
        else:
            # Fallback to progressive download
            durl = dash_info.get("durl", [])
            if durl:
                download_url = durl[0]["url"]
                return VideoInfo(
                    platform="bilibili",
                    video_id=video_id,
                    title=title,
                    author=author,
                    cover_url=cover_url,
                    duration=duration,
                    download_url=download_url,
                    is_dash=False,
                )
            else:
                raise ValueError("无法获取视频播放地址")
