# 视频爬虫工具 — 设计文档

> 创建日期: 2026-06-08
> 状态: 已批准

## 1. 项目概述

一个支持多平台视频无水印下载的 Web 应用，面向小团队使用，部署在云服务器上。

**支持平台（按优先级）**：
- 抖音 (Douyin)
- B站 (Bilibili)
- 小红书 (Xiaohongshu) — 后续扩展

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Element Plus | SPA 应用，现代化 UI |
| 后端 | FastAPI (Python 3.11+) | 异步 Web 框架 |
| 任务队列 | Celery + Redis | 异步处理视频下载 |
| 数据库 | PostgreSQL | 持久化存储 |
| 视频处理 | ffmpeg | DASH 流合并、转码 |
| 解析库 | httpx + BeautifulSoup | 平台 API 请求与 HTML 解析 |
| 降级方案 | Playwright | 无头浏览器（API 失效时） |
| 部署 | Docker Compose + Nginx | 容器化一键部署 |
| 认证 | JWT Token | 无状态认证 |

## 3. 系统架构

```
                      ┌──────────────────────────┐
                      │      Nginx (80/443)       │
                      │  前端静态文件 + 反向代理    │
                      └────────────┬─────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼────────┐  ┌───────▼───────┐  ┌─────────▼────────┐
    │  FastAPI (8000)  │  │  Redis (6379) │  │  PostgreSQL(5432)│
    │  用户认证/视频解析 │  │  消息队列/缓存  │  │  持久化存储       │
    │  任务管理         │  └───────┬───────┘  └──────────────────┘
    └─────────┬────────┘          │
              │           ┌───────▼───────┐
              └──────────► Celery Worker │
                          │  视频下载      │
                          │  去水印处理    │
                          │  ffmpeg 合并  │
                          └───────────────┘
```

## 4. 数据库设计

### users 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(50) | 用户名，唯一，非空 |
| password_hash | VARCHAR(255) | bcrypt 密码哈希 |
| role | VARCHAR(20) | admin / member |
| created_at | TIMESTAMP | 创建时间 |

### download_tasks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | FK → users.id | 创建者 |
| platform | VARCHAR(20) | douyin / bilibili / xiaohongshu |
| source_url | TEXT | 用户粘贴的原始链接 |
| video_title | VARCHAR(500) | 视频标题 |
| video_author | VARCHAR(200) | 作者昵称 |
| video_cover | TEXT | 封面图 URL |
| video_duration | INTEGER | 时长（秒） |
| status | VARCHAR(20) | pending / parsing / downloading / processing / completed / failed |
| file_path | VARCHAR(500) | 服务器上文件路径 |
| file_size | BIGINT | 文件大小（字节） |
| error_msg | TEXT | 失败原因 |
| created_at | TIMESTAMP | 创建时间 |
| finished_at | TIMESTAMP | 完成时间 |

## 5. API 设计

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /api/auth/login | 登录，返回 JWT | 否 |
| POST | /api/auth/register | 注册用户 | admin |
| POST | /api/video/parse | 解析视频链接 | 是 |
| POST | /api/video/download | 提交下载任务 | 是 |
| GET | /api/video/task/{id} | 查询任务状态 | 是 |
| GET | /api/video/task/{id}/file | 下载完成的视频 | 是 |
| GET | /api/video/history | 历史记录（分页） | 是 |
| WS | /ws/task/{id} | 实时进度推送 | 是 |

## 6. 平台解析策略

### 6.1 抖音

1. 跟随短链接重定向获取真实 URL，提取 video_id
2. 模拟移动端请求，调用抖音内部 API
3. 将无水印 URL 中的 `playwm` 替换为 `play` 得到无水印视频流
4. 关键：携带合法 User-Agent 和 Cookie

### 6.2 B站

1. 解析链接获取 BV 号或 aid
2. 调用 B站 API 获取视频信息 (view) 和播放地址 (playurl)
3. 返回 DASH 格式：video 数组（纯视频）+ audio 数组（纯音频）
4. 选择最高画质视频流 + 最高音质音频流
5. 使用 ffmpeg 合并：`ffmpeg -i video.mp4 -i audio.m4a -c copy output.mp4`
6. 关键：部分视频需要 Referer 头

### 6.3 小红书（后续）

1. 跟随短链接重定向，从页面提取 note_id
2. 调用内部 API，需携带签名参数 (X-S, X-T)
3. 从返回数据中提取无水印视频源
4. 降级方案：Playwright 无头浏览器拦截网络请求

### 降级方案（所有平台通用）

当 API 方式因反爬升级而失效时，使用 Playwright 无头浏览器：
- 模拟打开视频页面
- 拦截网络请求，捕获视频流地址
- 直接下载捕获到的 URL

## 7. 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录页 | /login | 用户名+密码登录 |
| 首页 | / | 输入链接 → 解析 → 下载 |
| 历史记录 | /history | 表格展示所有下载记录 |
| 用户管理 | /users | admin 可见，管理团队成员 |

## 8. 项目目录结构

```
pachongtools/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   ├── api/                 # 路由层
│   │   ├── services/            # 业务逻辑（平台解析器）
│   │   ├── tasks/               # Celery 任务
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
│   └── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── README.md
```

## 9. 开发阶段

| 阶段 | 内容 | 产出 |
|------|------|------|
| Phase 1 | 项目骨架 | FastAPI + Vue 初始化，Docker Compose |
| Phase 2 | 用户认证 | 登录/注册/JWT 鉴权 |
| Phase 3 | 抖音解析下载 | 解析 → 无水印源 → 下载 |
| Phase 4 | B站解析下载 | DASH 流 → ffmpeg 合并 |
| Phase 5 | 任务队列 | Celery 异步 + WebSocket 进度 |
| Phase 6 | 前端界面 | 页面开发 + 对接后端 |
| Phase 7 | 部署配置 | Nginx 配置 + Docker Compose |

## 10. 待定/后续

- 小红书平台支持（反爬较复杂，需后续研究）
- 下载格式选择（目前仅 MP4）
- 批量下载（多个链接同时提交）
