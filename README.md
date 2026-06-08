# 视频下载助手

支持多平台视频无水印下载的 Web 应用。方便小团队成员粘贴链接一键下载去水印视频。

## 支持平台

-   **抖音 (Douyin)** — 无水印下载
-   **B站 (Bilibili)** — DASH 流自动合并
-   **小红书 (Xiaohongshu)** — 规划中

## 技术栈

| 层级     | 技术                               |
| -------- | ---------------------------------- |
| 前端     | Vue 3 + Element Plus + Pinia       |
| 后端     | FastAPI (Python 3.11) + Celery      |
| 数据库   | PostgreSQL 16                       |
| 消息队列 | Redis 7                             |
| 视频处理 | ffmpeg                              |
| 部署     | Docker Compose + Nginx              |

## 快速开始

### 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Celery Worker (另一个终端)
cd backend
celery -A app.celery_app worker --loglevel=info

# 前端 (另一个终端)
cd frontend
npm install
npm run dev
```

前端访问 http://localhost:3000

### Docker Compose 部署

```bash
# 启动所有服务
docker compose up -d --build

# 初始化管理员
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# 设为 admin 角色
docker compose exec db psql -U postgres -d videocrawler \
  -c "UPDATE users SET role='admin' WHERE username='admin';"
```

## 项目结构

```
pachongtools/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 数据库连接
│   │   ├── celery_app.py        # Celery 配置
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── api/                 # 路由层
│   │   ├── services/            # 业务逻辑（各平台解析器）
│   │   ├── tasks/               # Celery 异步任务
│   │   └── utils/               # 工具函数
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/               # 页面组件
│   │   ├── components/          # 通用组件
│   │   ├── api/                 # API 请求封装
│   │   ├── router/              # 路由配置
│   │   └── store/               # Pinia 状态管理
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 功能

-   **视频解析**: 粘贴抖音/B站分享链接，自动解析视频信息
-   **无水印下载**: 获取无水印视频源地址
-   **B站 DASH 合并**: 自动下载视频流和音频流，用 ffmpeg 合并
-   **异步任务**: Celery 后台处理下载，不阻塞请求
-   **用户管理**: 支持多用户，管理员可添加/管理成员
-   **下载历史**: 查看和重新下载历史视频

## API 概览

| 方法   | 路径                     | 说明         |
| ------ | ------------------------ | ------------ |
| POST   | /api/auth/login          | 登录         |
| POST   | /api/auth/register       | 注册         |
| GET    | /api/auth/users          | 用户列表     |
| POST   | /api/video/parse         | 解析视频链接 |
| POST   | /api/video/download      | 提交下载任务 |
| GET    | /api/video/task/{id}     | 查询任务状态 |
| GET    | /api/video/task/{id}/file| 下载视频文件 |
| GET    | /api/video/history       | 下载历史     |
