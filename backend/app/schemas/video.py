from datetime import datetime

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    url: str = Field(..., description="视频分享链接")


class ParseResponse(BaseModel):
    platform: str
    video_id: str
    title: str
    author: str
    cover_url: str
    duration: int


class DownloadRequest(BaseModel):
    url: str = Field(..., description="视频分享链接")


class TaskResponse(BaseModel):
    id: str
    platform: str
    source_url: str
    video_title: str | None
    video_author: str | None
    status: str
    file_path: str | None
    error_msg: str | None
    created_at: datetime

    class Config:
        from_attributes = True
