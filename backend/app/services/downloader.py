import os
import subprocess
import uuid
from pathlib import Path

import httpx

from ..config import settings


async def download_video(
    download_url: str,
    filename_prefix: str = "video",
    headers: dict | None = None,
) -> str:
    """
    Download a video from URL to local storage.
    Returns the file path.
    """
    os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)

    file_path = Path(settings.DOWNLOAD_DIR) / f"{filename_prefix}_{uuid.uuid4().hex[:8]}.mp4"

    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Mobile/15E148 Safari/604.1"
        ),
    }
    request_headers = {**default_headers, **(headers or {})}

    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        async with client.stream("GET", download_url, headers=request_headers) as response:
            response.raise_for_status()
            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    return str(file_path)


def merge_video_audio(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Use ffmpeg to merge DASH video and audio streams.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 合并失败: {result.stderr}")

    # Clean up temp files
    os.remove(video_path)
    os.remove(audio_path)

    return output_path
