import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
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
    """Submit a video download task."""
    url = req.url.strip()

    # Determine platform
    if "douyin.com" in url:
        platform = "douyin"
    elif "bilibili.com" in url or "b23.tv" in url:
        platform = "bilibili"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的平台链接",
        )

    # Parse to get video info
    try:
        if platform == "douyin":
            from ..services.parser_douyin import parse_douyin_video
            info = await parse_douyin_video(url)
        else:
            from ..services.parser_bilibili import parse_bilibili_video
            info = await parse_bilibili_video(url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"视频解析失败: {str(e)}",
        )

    # Create task record
    task = DownloadTask(
        id=uuid.uuid4(),
        user_id=current_user.id,
        platform=platform,
        source_url=url,
        video_title=info.title,
        video_author=info.author,
        video_cover=info.cover_url,
        video_duration=info.duration,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Submit to Celery
    from ..tasks.download import download_video_task
    download_video_task.delay(str(task.id), url, platform)

    # Update status
    task.status = "parsing"
    await db.commit()
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在",
        )

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the completed video file."""
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
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
