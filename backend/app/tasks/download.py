import os
import uuid
from datetime import datetime, timezone

from celery import Task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..config import settings
from ..models.task import DownloadTask

sync_engine = create_engine(settings.DATABASE_URL_SYNC)


class DownloadTaskBase(Task):
    """Base task with database session management."""
    _db: Session | None = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = Session(sync_engine)
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DownloadTaskBase,
    name="download_video",
    track_started=True,
)
def download_video_task(self, task_id: str, url: str, platform: str):
    """Celery task: download video from given URL."""
    import asyncio

    task = self.db.execute(
        select(DownloadTask).where(DownloadTask.id == task_id)
    ).scalar_one_or_none()

    if not task:
        return {"error": "Task not found"}

    task.status = "downloading"
    self.db.commit()

    try:
        # Re-parse to get fresh download URL
        if platform == "douyin":
            from ..services.parser_douyin import parse_douyin_video
            info = asyncio.run(parse_douyin_video(url))
        elif platform == "bilibili":
            from ..services.parser_bilibili import parse_bilibili_video
            info = asyncio.run(parse_bilibili_video(url))
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        from ..services.downloader import download_video, merge_video_audio

        if info.is_dash and info.audio_url:
            # B站 DASH: download video + audio separately, then merge
            self.update_state(state="DOWNLOADING", meta={"progress": 30, "stage": "下载视频流"})
            video_path = asyncio.run(
                download_video(info.download_url, filename_prefix=f"bilibili_v_{task_id[:8]}",
                             headers={"Referer": "https://www.bilibili.com/"})
            )

            self.update_state(state="DOWNLOADING", meta={"progress": 60, "stage": "下载音频流"})
            audio_path = asyncio.run(
                download_video(info.audio_url, filename_prefix=f"bilibili_a_{task_id[:8]}",
                             headers={"Referer": "https://www.bilibili.com/"})
            )

            task.status = "processing"
            self.db.commit()
            self.update_state(state="PROCESSING", meta={"progress": 80, "stage": "合并音视频"})

            output_path = os.path.join(
                settings.DOWNLOAD_DIR, f"{task_id}_{uuid.uuid4().hex[:8]}.mp4"
            )
            final_path = merge_video_audio(video_path, audio_path, output_path)
        else:
            self.update_state(state="DOWNLOADING", meta={"progress": 30, "stage": "下载视频"})
            final_path = asyncio.run(
                download_video(info.download_url, filename_prefix=f"{platform}_{task_id[:8]}")
            )

        # Update task record
        task.status = "completed"
        task.file_path = final_path
        task.file_size = os.path.getsize(final_path)
        task.finished_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "status": "completed",
            "file_path": final_path,
            "file_size": task.file_size,
        }

    except Exception as e:
        task.status = "failed"
        task.error_msg = str(e)
        task.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        raise
