import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db, gen_uuid
from ..config import settings
from ..models.user import User
from ..models.task import DownloadTask
from ..schemas.video import ParseRequest, ParseResponse, DownloadRequest, TaskResponse
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/parse", response_model=ParseResponse)
async def parse_video_url(
    req: ParseRequest,
    current_user: User = Depends(get_current_user),
):
    """解析视频链接，返回视频信息但不下载"""
    url = req.url.strip()

    if "douyin.com" in url:
        from ..services.parser_douyin import parse_douyin_video
        info = await parse_douyin_video(url)
    elif "bilibili.com" in url or "b23.tv" in url:
        from ..services.parser_bilibili import parse_bilibili_video
        info = await parse_bilibili_video(url)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的平台链接，请提供抖音、B站链接",
        )

    return ParseResponse(
        platform=info.platform,
        video_id=info.video_id,
        title=info.title,
        author=info.author,
        cover_url=info.cover_url,
        duration=info.duration,
    )


@router.post("/download", response_model=TaskResponse)
async def submit_download(
    req: DownloadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parse + Download video directly (synchronous)."""
    url = req.url.strip()

    # Determine platform
    if "douyin.com" in url:
        platform = "douyin"
        from ..services.parser_douyin import parse_douyin_video
    elif "bilibili.com" in url or "b23.tv" in url:
        platform = "bilibili"
        from ..services.parser_bilibili import parse_bilibili_video
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的平台链接",
        )

    # Create task record
    task = DownloadTask(
        id=gen_uuid(),
        user_id=current_user.id,
        platform=platform,
        source_url=url,
        status="parsing",
    )
    db.add(task)
    await db.commit()

    try:
        # Parse video info
        if platform == "douyin":
            info = await parse_douyin_video(url)
        else:
            info = await parse_bilibili_video(url)

        task.video_title = info.title
        task.video_author = info.author
        task.video_cover = info.cover_url
        task.video_duration = info.duration
        task.status = "downloading"
        await db.commit()

        # Download directly
        from ..services.downloader import download_video, merge_video_audio

        if info.is_dash and info.audio_url:
            # B站 DASH
            video_path = await download_video(
                info.download_url,
                filename_prefix=f"bilibili_v_{task.id[:8]}",
                headers={"Referer": "https://www.bilibili.com/"},
            )
            audio_path = await download_video(
                info.audio_url,
                filename_prefix=f"bilibili_a_{task.id[:8]}",
                headers={"Referer": "https://www.bilibili.com/"},
            )
            task.status = "processing"
            await db.commit()

            output_path = os.path.join(settings.DOWNLOAD_DIR, f"{task.id}_merged.mp4")
            final_path = merge_video_audio(video_path, audio_path, output_path)
        else:
            final_path = await download_video(
                info.download_url,
                filename_prefix=f"{platform}_{task.id[:8]}",
            )

        # Mark completed
        task.status = "completed"
        task.file_path = final_path
        task.file_size = os.path.getsize(final_path)
        task.finished_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as e:
        task.status = "failed"
        task.error_msg = str(e)[:500]
        task.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载失败: {str(e)[:200]}",
        )

    await db.refresh(task)
    return TaskResponse(
        id=str(task.id),
        platform=task.platform,
        source_url=task.source_url,
        video_title=task.video_title,
        video_author=task.video_author,
        status=task.status,
        file_path=task.file_path,
        error_msg=task.error_msg,
        created_at=task.created_at,
    )


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get download task status."""
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    return TaskResponse(
        id=str(task.id),
        platform=task.platform,
        source_url=task.source_url,
        video_title=task.video_title,
        video_author=task.video_author,
        status=task.status,
        file_path=task.file_path,
        error_msg=task.error_msg,
        created_at=task.created_at,
    )


@router.get("/task/{task_id}/file")
async def download_task_file(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the completed video file. No auth required — task ID acts as secret."""
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.status == "completed",
        )
    )
    task = result.scalar_one_or_none()
    if not task or not task.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或尚未完成下载",
        )

    filename = f"{task.video_title or 'video'}.mp4"
    return FileResponse(task.file_path, filename=filename, media_type="video/mp4")


@router.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's download history."""
    result = await db.execute(
        select(DownloadTask)
        .where(DownloadTask.user_id == current_user.id)
        .order_by(DownloadTask.created_at.desc())
        .limit(50)
    )
    tasks = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "platform": t.platform,
            "source_url": t.source_url,
            "video_title": t.video_title,
            "video_author": t.video_author,
            "status": t.status,
            "file_path": t.file_path,
            "error_msg": t.error_msg,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        }
        for t in tasks
    ]
