# 视频下载助手

支持多平台视频无水印下载的 Web 应用。粘贴分享链接，一键下载去水印视频。

## 支持平台

- **抖音 (Douyin)** — 无水印下载 ✅
- **B站 (Bilibili)** — DASH 流自动合并 ✅（需要 ffmpeg）
- **小红书 (Xiaohongshu)** — 规划中

## 技术栈

| 层级   | 技术                            |
| ------ | ------------------------------- |
| 前端   | Vue 3 + Element Plus + Pinia    |
| 后端   | FastAPI (Python 3.10+)          |
| 数据库 | SQLite（默认）/ PostgreSQL 可选 |
| 视频处理 | ffmpeg（仅 B站合并需要）      |
| 部署   | Docker Compose + Nginx          |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- ffmpeg（仅 B站视频合并需要，抖音下载不需要）

### 本地运行（3 步）

```bash
# 1. 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. 前端（另一个终端）
cd frontend
npm install
npm run dev

# 3. 打开浏览器
# http://localhost:3000
```

首次使用时，在网页上注册一个账号即可登录。

> 默认使用 SQLite 数据库（`backend/videocrawler.db`），无需安装 PostgreSQL/Redis。
> 下载的视频保存在 `backend/downloads/` 目录。

### Docker Compose 部署（生产环境）

```bash
# 启动所有服务（PostgreSQL + Redis + Nginx）
docker compose up -d --build

# 初始化管理员
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# 设为 admin 角色
docker compose exec db psql -U postgres -d videocrawler \
  -c "UPDATE users SET role='admin' WHERE username='admin';"
```

## 配置

通过环境变量或 `backend/.env` 文件配置：

| 变量                        | 默认值                    | 说明                       |
| --------------------------- | ------------------------- | -------------------------- |
| `DB_TYPE`                   | `sqlite`                  | `sqlite` 或 `postgres`     |
| `DATABASE_URL`              | `sqlite+aiosqlite:///./videocrawler.db` | 数据库连接串     |
| `SECRET_KEY`                | `change-me-in-production...` | JWT 密钥，生产环境必须修改 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440`                  | 登录有效期（分钟）         |
| `DOWNLOAD_DIR`              | `./downloads`             | 视频保存目录               |

## 项目结构

```
pachongtools/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 数据库连接（SQLite/PostgreSQL）
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── api/                 # 路由层（auth, video）
│   │   ├── services/            # 业务逻辑（各平台解析器、下载器）
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

- **视频解析**: 粘贴抖音/B站分享链接，自动解析视频信息（标题、作者、封面、时长）
- **无水印下载**: 自动获取无水印视频源地址
- **B站 DASH 合并**: 自动下载视频流和音频流，用 ffmpeg 合并
- **用户管理**: 支持多用户，管理员可添加/管理成员
- **下载历史**: 查看和重新下载历史视频

## API 概览

| 方法 | 路径                      | 说明         |
| ---- | ------------------------- | ------------ |
| POST | /api/auth/login           | 登录         |
| POST | /api/auth/register        | 注册         |
| GET  | /api/auth/users           | 用户列表     |
| POST | /api/video/parse          | 解析视频链接 |
| POST | /api/video/download       | 提交下载任务 |
| GET  | /api/video/task/{id}      | 查询任务状态 |
| GET  | /api/video/task/{id}/file | 下载视频文件 |
| GET  | /api/video/history        | 下载历史     |

## 免责声明

本项目仅用于学习和个人使用，请勿用于商业用途或侵犯他人版权。使用本项目下载视频时，请遵守相关平台的服务条款和当地法律法规。
