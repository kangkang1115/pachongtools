# 视频爬虫工具 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个支持抖音和 B站 视频无水印下载的 Web 应用，小团队使用，部署到云服务器。

**Architecture:** FastAPI 后端提供 REST API + WebSocket，Celery 异步处理视频下载任务，Vue 3 前端提供用户界面，PostgreSQL 存储数据，Redis 做消息队列，Docker Compose 容器化部署。

**Tech Stack:** Python 3.11+, FastAPI, Celery, Redis, PostgreSQL, ffmpeg, Vue 3, Element Plus, Pinia, Vue Router, Docker, Nginx

---

## 文件结构总览

```
pachongtools/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口，挂载路由，CORS，WebSocket
│   │   ├── config.py            # 环境变量读取 (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── celery_app.py        # Celery 实例配置
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py          # User 模型
│   │   │   └── task.py          # DownloadTask 模型
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # LoginRequest, TokenResponse 等
│   │   │   └── video.py         # ParseResponse, TaskResponse 等
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # /api/auth/* 路由
│   │   │   └── video.py         # /api/video/* 路由 + WebSocket
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── parser_douyin.py # 抖音解析器
│   │   │   ├── parser_bilibili.py # B站解析器
│   │   │   └── downloader.py    # 通用下载器 + ffmpeg 合并
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── download.py      # Celery 下载任务
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── security.py      # JWT 生成/验证，密码哈希
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/                 # (后续可加数据库迁移)
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── store/
│   │   │   └── user.js
│   │   ├── api/
│   │   │   ├── index.js         # axios 实例 + 拦截器
│   │   │   ├── auth.js          # 登录/注册 API
│   │   │   └── video.js         # 视频解析/下载 API
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── Home.vue
│   │   │   ├── History.vue
│   │   │   └── Users.vue
│   │   └── components/
│   │       ├── VideoCard.vue
│   │       └── DownloadProgress.vue
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

## Phase 1: 项目骨架搭建

### Task 1: 创建后端项目骨架

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/Dockerfile`

- [ ] **Step 1: 创建 requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
psycopg2-binary==2.9.9
celery[redis]==5.4.0
redis==5.0.7
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.0
beautifulsoup4==4.12.3
pydantic-settings==2.3.4
python-multipart==0.0.9
websockets==12.0
```

- [ ] **Step 2: 创建 backend/app/__init__.py**

```python
```

- [ ] **Step 3: 创建 backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/videocrawler"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/videocrawler"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Download
    DOWNLOAD_DIR: str = "/data/downloads"

    # App
    APP_NAME: str = "视频下载助手"
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: 创建 backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 5: 创建 backend/app/main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup on shutdown
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "name": settings.APP_NAME}
```

- [ ] **Step 6: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7: 验证后端可启动**

Run:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Expected: 看到 "Application startup complete" 日志，访问 `http://localhost:8000/api/health` 返回 `{"status":"ok","name":"视频下载助手"}`

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: create backend project skeleton with FastAPI"
```

### Task 2: 创建前端项目骨架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: 使用 Vite 创建 Vue 3 项目**

Run:
```bash
cd frontend
npm create vite@latest . -- --template vue
npm install
```

- [ ] **Step 2: 安装依赖**

Run:
```bash
cd frontend
npm install element-plus@2.9.1 pinia@2.2.0 vue-router@4.4.0 axios@1.7.2 @element-plus/icons-vue@2.3.1
```

- [ ] **Step 3: 创建 frontend/vite.config.js**（替换生成的默认文件）

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 4: 创建 frontend/src/main.js**（替换生成的默认文件）

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// 全局注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

- [ ] **Step 5: 创建 frontend/src/App.vue**

```vue
<template>
  <router-view />
</template>

<script setup>
</script>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f5f7fa;
}
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>
```

- [ ] **Step 6: 创建 frontend/src/router/index.js**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
  },
  // 其他路由后续添加
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 7: 创建 placeholder Login.vue**

Create `frontend/src/views/Login.vue`:
```vue
<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>视频下载助手</h2>
      <el-form>
        <el-form-item>
          <el-input placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input placeholder="密码" type="password" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  padding: 20px;
}
.login-card h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}
</style>
```

- [ ] **Step 8: 创建 frontend/Dockerfile**

```dockerfile
FROM node:20-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 9: 验证前端可启动**

Run:
```bash
cd frontend
npm run dev
```
Expected: 访问 `http://localhost:3000` 看到登录页面

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: create frontend project skeleton with Vue 3 + Element Plus"
```

### Task 3: Docker Compose 配置

**Files:**
- Create: `docker-compose.yml`
- Create: `nginx.conf`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: videocrawler
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/videocrawler
      DATABASE_URL_SYNC: postgresql+psycopg2://postgres:postgres@db:5432/videocrawler
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: change-me-in-production
      DOWNLOAD_DIR: /data/downloads
    volumes:
      - downloads:/data/downloads
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/videocrawler
      DATABASE_URL_SYNC: postgresql+psycopg2://postgres:postgres@db:5432/videocrawler
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: change-me-in-production
      DOWNLOAD_DIR: /data/downloads
    volumes:
      - downloads:/data/downloads
    depends_on:
      - db
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  pgdata:
  downloads:
```

- [ ] **Step 2: 创建 nginx.conf**（用于前端容器内代理 API 请求）

```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # 前端 SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 代理 API 到后端
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 代理 WebSocket
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

- [ ] **Step 3: 更新 frontend/Dockerfile** 复制 nginx.conf

```dockerfile
FROM node:20-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

注意：nginx.conf 放在项目根目录，需要在 docker-compose.yml 同级目录构建。修正：将 nginx.conf 放在 frontend/ 目录下，或调整 Dockerfile 的 COPY 路径。这里采用放在 frontend/ 下。

- [ ] **Step 4: 验证 Docker Compose**

Run:
```bash
docker-compose up -d --build
docker-compose ps
```
Expected: 看到 4 个服务 (db, redis, backend, frontend) 状态为 Up。celery-worker 可能因缺少 celery_app 模块暂时失败。

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml frontend/nginx.conf frontend/Dockerfile
git commit -m "feat: add Docker Compose configuration"
```

---

## Phase 2: 用户认证

### Task 4: 用户模型和数据库初始化

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`

- [ ] **Step 1: 创建 backend/app/models/__init__.py**

```python
from .user import User
from .task import DownloadTask

__all__ = ["User", "DownloadTask"]
```

- [ ] **Step 2: 创建 backend/app/models/user.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member"
    )  # admin / member
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 3: Update backend/app/models/__init__.py** 让它能正常工作（Task 模型还没建，先注释掉）

```python
from .user import User

__all__ = ["User"]
```

- [ ] **Step 4: 更新 backend/app/main.py 导入 models 确保表被创建**

在 `backend/app/main.py` 顶部 (在 `from .database import engine, Base` 之后) 添加:
```python
from .models import User  # noqa: ensure models are loaded for table creation
```

完整文件变为:
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .models import User  # noqa: ensure models are loaded for table creation


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "name": settings.APP_NAME}
```

- [ ] **Step 5: 验证启动后数据库自动建表**

Run:
```bash
docker-compose up -d db
cd backend
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/videocrawler uvicorn app.main:app --host 0.0.0.0 --port 8000
# 检查 PostgreSQL 中是否创建了 users 表
docker-compose exec db psql -U postgres -d videocrawler -c "\dt"
```
Expected: 输出中包含 `users` 表。

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/ backend/app/main.py
git commit -m "feat: add User model with auto table creation"
```

### Task 5: JWT 和安全工具

**Files:**
- Create: `backend/app/utils/__init__.py`
- Create: `backend/app/utils/security.py`

- [ ] **Step 1: 创建 backend/app/utils/__init__.py**

```python
```

- [ ] **Step 2: 创建 backend/app/utils/security.py**

```python
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from ..config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/
git commit -m "feat: add JWT and password hashing utilities"
```

### Task 6: Auth Schemas 和路由

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`

- [ ] **Step 1: 创建 backend/app/schemas/__init__.py**

```python
```

- [ ] **Step 2: 创建 backend/app/schemas/auth.py**

```python
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserResponse(BaseModel):
    id: str
    username: str
    role: str

    class Config:
        from_attributes = True
```

- [ ] **Step 3: 创建 backend/app/api/__init__.py**

```python
```

- [ ] **Step 4: 创建 backend/app/api/auth.py**

```python
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from ..utils.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    return TokenResponse(
        access_token=access_token,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == req.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    user = User(
        id=uuid.uuid4(),
        username=req.username,
        password_hash=hash_password(req.password),
        role="member",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    return TokenResponse(
        access_token=access_token,
        username=user.username,
        role=user.role,
    )
```

- [ ] **Step 5: 在 backend/app/main.py 中挂载路由**

更新 `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .models.user import User  # noqa
from .api.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "name": settings.APP_NAME}
```

- [ ] **Step 6: 创建 backend/app/utils/dependencies.py** (依赖注入，独立模块避免循环引用)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from .security import decode_access_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user
```

- [ ] **Step 7: 验证登录/注册 API**

Run:
```bash
# 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 另一个终端测试
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 应返回 {"access_token":"...","token_type":"bearer","username":"admin","role":"member"}

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```
Expected: 注册返回 Token，登录返回 Token。401 当密码错误时。

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ backend/app/main.py backend/app/utils/
git commit -m "feat: add auth routes for login and register with JWT"
```

---

## Phase 3: 抖音解析下载

### Task 7: 抖音解析器

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/parser_douyin.py`

- [ ] **Step 1: 创建 backend/app/services/__init__.py**

```python
```

- [ ] **Step 2: 创建 backend/app/services/parser_douyin.py**

```python
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
    download_url: str  # watermark-free URL


DOUYIN_SHARE_PATTERN = re.compile(
    r"https?://v\.douyin\.com/(\w+)"
)

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

    Strategy:
    1. Follow short link redirects to get the full URL with video_id
    2. Use Douyin's internal API with mobile headers
    3. Replace 'playwm' with 'play' in the video URL to remove watermark
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        # Step 1: Follow short link to get video ID
        response = await client.get(url, headers=DOUYIN_MOBILE_HEADERS)
        final_url = str(response.url)

        # Extract video_id from final URL (e.g. /video/7123456789012345678)
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
        # Priority: download_addr (usually watermark-free) > play_addr (with watermark)
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
```

- [ ] **Step 3: 添加解析器单元测试手动验证**

Run:
```bash
cd backend
python -c "
import asyncio
from app.services.parser_douyin import parse_douyin_video

async def test():
    # 用实际的抖音分享链接测试
    url = 'https://v.douyin.com/xxxxx/'  # 替换为真实链接
    info = await parse_douyin_video(url)
    print(info)

asyncio.run(test())
"
```

Expected: （需真实链接）返回 VideoInfo 对象，包含标题、作者、无水印URL等信息。

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/
git commit -m "feat: add Douyin video parser service"
```

### Task 8: 通用下载器和 Video Schemas

**Files:**
- Create: `backend/app/services/downloader.py`
- Create: `backend/app/schemas/video.py`

- [ ] **Step 1: 创建 backend/app/services/downloader.py**

```python
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
```

- [ ] **Step 2: 创建 backend/app/schemas/video.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/downloader.py backend/app/schemas/video.py
git commit -m "feat: add generic video downloader and video schemas"
```

### Task 9: 视频 API 路由（解析 + 下载）

**Files:**
- Create: `backend/app/api/video.py`

- [ ] **Step 1: 创建 backend/app/api/video.py**

```python
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.video import ParseRequest, ParseResponse
from ..services.parser_douyin import parse_douyin_video
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
        info = await parse_douyin_video(url)
    elif "bilibili.com" in url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="B站支持即将上线",
        )
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
```

- [ ] **Step 2: 在 backend/app/main.py 中挂载 video 路由**

在 `main.py` 中添加:
```python
from .api.video import router as video_router

# 在 app.include_router(auth_router) 之后添加:
app.include_router(video_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/video.py backend/app/main.py
git commit -m "feat: add video parse API endpoint"
```

---

## Phase 4: B站解析下载

### Task 10: B站解析器

**Files:**
- Create: `backend/app/services/parser_bilibili.py`

- [ ] **Step 1: 创建 backend/app/services/parser_bilibili.py**

```python
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
    Parse a Bilibili video URL and return video/audio DASH stream info.

    Strategy:
    1. Extract BV number or aid from the URL
    2. Call Bilibili API to get video info (cid, title, author)
    3. Call playurl API to get DASH streams (separate video + audio)
    4. Return best quality video and audio URLs for merging
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

        # Step 2: Get play URL (DASH format)
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
            # Fallback: try without fnval for non-DASH format
            if bv_match:
                fallback_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}"
            else:
                fallback_url = f"https://api.bilibili.com/x/player/playurl?aid={aid}&cid={cid}"
            play_resp = await client.get(fallback_url, headers=play_headers)
            play_resp.raise_for_status()
            play_data = play_resp.json()

        dash_info = play_data.get("data", {})

        # Step 3: Extract best DASH streams
        download_url = ""
        if "dash" in dash_info:
            # Modern DASH format - return JSON with video+audio URLs for later merging
            dash = dash_info["dash"]
            video_streams = dash.get("video", [])
            audio_streams = dash.get("audio", [])

            if video_streams and audio_streams:
                # Pick highest quality video
                best_video = video_streams[0]  # B站返回已按质量排序
                best_audio = audio_streams[0]

                download_url = best_video.get("base_url", "") or best_video.get("baseUrl", "")
                # Store audio URL separately for merging
                # We'll use the video_url as download_url and let the caller handle audio
        else:
            # Fallback to progressive download (older format)
            durl = dash_info.get("durl", [])
            if durl:
                download_url = durl[0]["url"]
            else:
                raise ValueError("无法获取视频播放地址")

        if not download_url:
            raise ValueError("无法获取视频下载地址")

        return VideoInfo(
            platform="bilibili",
            video_id=video_id,
            title=title,
            author=author,
            cover_url=cover_url,
            duration=duration,
            download_url=download_url,
        )
```

**注意**：B站的 DASH 格式处理比较特殊，因为视频和音频是分离的。上面的解析器返回的是视频流的 URL。音频流的 URL 需要在下载任务中单独处理。这里我们先简化处理，把 B站解析器的返回值扩展一下。

更新 `backend/app/services/parser_douyin.py` 中的 `VideoInfo`：

```python
@dataclass
class VideoInfo:
    platform: str
    video_id: str
    title: str
    author: str
    cover_url: str
    duration: int
    download_url: str
    # B站 DASH 专用字段
    audio_url: str = ""  # B站音频流 URL（如果有的话）
    is_dash: bool = False  # 是否需要合并
```

然后更新 `parser_bilibili.py` 中的设置：

```python
# 在返回 VideoInfo 时:
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
```

- [ ] **Step 2: 更新 backend/app/services/parser_douyin.py** 的 VideoInfo 类

```python
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
```

- [ ] **Step 3: 更新 backend/app/api/video.py** 支持 B站解析

在 `parse_video_url` 函数的平台判断中添加 B站分支：

```python
elif "bilibili.com" in url or "b23.tv" in url:
    from ..services.parser_bilibili import parse_bilibili_video
    info = await parse_bilibili_video(url)
```

替换原来的 `HTTPException(status_code=501)` 部分。

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/parser_bilibili.py backend/app/services/parser_douyin.py backend/app/api/video.py
git commit -m "feat: add Bilibili video parser with DASH support"
```

---

## Phase 5: 任务队列

### Task 11: Celery 配置和下载任务

**Files:**
- Create: `backend/app/celery_app.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/download.py`

- [ ] **Step 1: 创建 backend/app/celery_app.py**

```python
from celery import Celery
from .config import settings

celery_app = Celery(
    "videocrawler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 2: 创建 backend/app/models/task.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class DownloadTask(Base):
    __tablename__ = "download_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    video_title: Mapped[str | None] = mapped_column(String(500))
    video_author: Mapped[str | None] = mapped_column(String(200))
    video_cover: Mapped[str | None] = mapped_column(Text)
    video_duration: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, parsing, downloading, processing, completed, failed
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    error_msg: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", backref="download_tasks")
```

- [ ] **Step 3: 更新 backend/app/models/__init__.py**

```python
from .user import User
from .task import DownloadTask

__all__ = ["User", "DownloadTask"]
```

- [ ] **Step 4: 更新 backend/app/main.py** 导入新模型

将 `from .models.user import User` 改为 `from .models import User, DownloadTask`

- [ ] **Step 5: 创建 backend/app/tasks/__init__.py**

```python
```

- [ ] **Step 6: 创建 backend/app/tasks/download.py**

```python
import os
import uuid

from celery import Task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..config import settings
from ..models.task import DownloadTask

# Sync engine for Celery tasks
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
    from datetime import datetime, timezone

    # Update status to downloading
    task = self.db.execute(
        select(DownloadTask).where(DownloadTask.id == task_id)
    ).scalar_one_or_none()

    if not task:
        return {"error": "Task not found"}

    task.status = "downloading"
    self.db.commit()

    try:
        # Re-parse to get fresh download URL (some URLs expire)
        if platform == "douyin":
            import asyncio
            from ..services.parser_douyin import parse_douyin_video
            info = asyncio.run(parse_douyin_video(url))
        elif platform == "bilibili":
            import asyncio
            from ..services.parser_bilibili import parse_bilibili_video
            info = asyncio.run(parse_bilibili_video(url))
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        # Download video
        import asyncio
        from ..services.downloader import download_video, merge_video_audio
        import httpx

        if info.is_dash and info.audio_url:
            # B站 DASH: download video + audio separately, then merge
            task.status = "downloading"
            self.db.commit()
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
```

- [ ] **Step 7: 在 backend/app/api/video.py 中添加下载端点**

更新 `backend/app/api/video.py`，在已有代码后添加：

```python
from ..schemas.video import DownloadRequest, TaskResponse
from ..models.task import DownloadTask
from ..tasks.download import download_video_task


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

    # Parse to get video info for the task record
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
    from sqlalchemy import select

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
```

	@router.get("/task/{task_id}/file")
	async def download_task_file(
	    task_id: str,
	    current_user: User = Depends(get_current_user),
	    db: AsyncSession = Depends(get_db),
	):
	    """Download the completed video file."""
	    from fastapi.responses import FileResponse
	    from sqlalchemy import select

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
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/celery_app.py backend/app/models/task.py backend/app/models/__init__.py backend/app/main.py backend/app/tasks/ backend/app/api/video.py
git commit -m "feat: add Celery task queue for async video download"
```

---

## Phase 6: 前端界面

### Task 12: 前端 API 层和状态管理

**Files:**
- Create: `frontend/src/api/index.js`
- Create: `frontend/src/api/auth.js`
- Create: `frontend/src/api/video.js`
- Create: `frontend/src/store/user.js`

- [ ] **Step 1: 创建 frontend/src/api/index.js**

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 2: 创建 frontend/src/api/auth.js**

```javascript
import api from './index'

export function login(username, password) {
  return api.post('/auth/login', { username, password })
}

export function register(username, password) {
  return api.post('/auth/register', { username, password })
}
```

- [ ] **Step 3: 创建 frontend/src/api/video.js**

```javascript
import api from './index'

export function parseVideo(url) {
  return api.post('/video/parse', { url })
}

export function downloadVideo(url) {
  return api.post('/video/download', { url })
}

export function getTaskStatus(taskId) {
  return api.get(`/video/task/${taskId}`)
}
```

- [ ] **Step 4: 创建 frontend/src/store/user.js**

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function loginAction(username, password) {
    const res = await loginApi(username, password)
    const { access_token, username: name, role } = res.data
    token.value = access_token
    user.value = { username: name, role }
    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ username: name, role }))
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { user, token, isLoggedIn, isAdmin, loginAction, logout }
})
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ frontend/src/store/
git commit -m "feat: add frontend API layer and user store"
```

### Task 13: 登录页和路由守卫

**Files:**
- Modify: `frontend/src/views/Login.vue`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 更新 frontend/src/views/Login.vue** 完整实现

```vue
<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <div class="logo-section">
        <el-icon :size="48" color="#409EFF"><VideoCameraFilled /></el-icon>
        <h2>视频下载助手</h2>
        <p class="subtitle">支持抖音 · B站 无水印下载</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, VideoCameraFilled } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.loginAction(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.login-card {
  width: 420px;
  padding: 40px;
  border-radius: 12px;
}
.logo-section {
  text-align: center;
  margin-bottom: 32px;
}
.logo-section h2 {
  margin: 12px 0 4px;
  color: #303133;
  font-size: 24px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
  margin: 0;
}
</style>
```

- [ ] **Step 2: 更新 frontend/src/router/index.js** 添加路由守卫

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/Users.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')

  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }

  if (to.meta.guest && token) {
    return next('/')
  }

  if (to.meta.requiresAdmin && user?.role !== 'admin') {
    return next('/')
  }

  next()
})

export default router
```

- [ ] **Step 3: 更新 frontend/src/App.vue** 添加整体布局

```vue
<template>
  <router-view v-if="!isAuthPage" />
  <router-view v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isAuthPage = computed(() => route.path === '/login')
</script>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f5f7fa;
}
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>
```

实际上，登录页也通过 `<router-view />` 渲染。App.vue 可以直接简化为:

```vue
<template>
  <router-view />
</template>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/Login.vue frontend/src/router/index.js frontend/src/App.vue
git commit -m "feat: implement login page with route guards"
```

### Task 14: 首页（视频解析 + 下载）

**Files:**
- Create: `frontend/src/views/Home.vue`
- Create: `frontend/src/components/VideoCard.vue`
- Create: `frontend/src/components/DownloadProgress.vue`

- [ ] **Step 1: 创建 frontend/src/views/Home.vue**

```vue
<template>
  <el-container class="home-container">
    <!-- Header -->
    <el-header class="home-header">
      <div class="header-left">
        <el-icon :size="28" color="#409EFF"><VideoCameraFilled /></el-icon>
        <h3>视频下载助手</h3>
      </div>
      <div class="header-right">
        <el-button type="text" @click="$router.push('/history')">
          <el-icon><Clock /></el-icon>
          下载历史
        </el-button>
        <el-button v-if="userStore.isAdmin" type="text" @click="$router.push('/users')">
          <el-icon><Setting /></el-icon>
          用户管理
        </el-button>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            {{ userStore.user?.username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="home-main">
      <div class="main-content">
        <!-- URL Input Section -->
        <el-card class="input-card">
          <div class="input-section">
            <el-input
              v-model="videoUrl"
              size="large"
              placeholder="粘贴抖音或B站视频分享链接，支持 v.douyin.com / b23.tv 等"
              clearable
              @keyup.enter="handleParse"
            >
              <template #prefix>
                <el-icon><Link /></el-icon>
              </template>
              <template #append>
                <el-button
                  type="primary"
                  :loading="parsing"
                  :disabled="!videoUrl.trim()"
                  @click="handleParse"
                >
                  <el-icon v-if="!parsing"><Search /></el-icon>
                  {{ parsing ? '解析中...' : '解析视频' }}
                </el-button>
              </template>
            </el-input>
          </div>
        </el-card>

        <!-- Video Info Card -->
        <div v-if="videoInfo" class="video-info-section">
          <VideoCard :info="videoInfo" :downloading="downloading" @download="handleDownload" />
        </div>

        <!-- Download Progress -->
        <DownloadProgress
          v-if="activeTasks.length > 0"
          :tasks="activeTasks"
        />
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCameraFilled, Link, Search, Clock, Setting, ArrowDown } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { parseVideo, downloadVideo, getTaskStatus } from '../api/video'
import VideoCard from '../components/VideoCard.vue'
import DownloadProgress from '../components/DownloadProgress.vue'

const router = useRouter()
const userStore = useUserStore()

const videoUrl = ref('')
const parsing = ref(false)
const downloading = ref(false)
const videoInfo = ref(null)
const activeTasks = ref([])

async function handleParse() {
  if (!videoUrl.value.trim()) return

  parsing.value = true
  videoInfo.value = null

  try {
    const res = await parseVideo(videoUrl.value.trim())
    videoInfo.value = res.data
    ElMessage.success('视频解析成功')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '视频解析失败，请检查链接')
  } finally {
    parsing.value = false
  }
}

async function handleDownload() {
  downloading.value = true

  try {
    const res = await downloadVideo(videoUrl.value.trim())
    const task = {
      id: res.data.id,
      title: videoInfo.value.title,
      status: 'parsing',
      platform: videoInfo.value.platform,
    }
    activeTasks.value.unshift(task)

    // Poll for task status
    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await getTaskStatus(res.data.id)
        const t = activeTasks.value.find(t => t.id === res.data.id)
        if (t) {
          t.status = statusRes.data.status
        }

        if (statusRes.data.status === 'completed') {
          clearInterval(pollInterval)
          ElMessage.success(`「${videoInfo.value.title}」下载完成！`)

          // Trigger browser download
          const a = document.createElement('a')
          a.href = `/api/video/task/${res.data.id}/file`
          a.download = `${videoInfo.value.title}.mp4`
          a.click()
        } else if (statusRes.data.status === 'failed') {
          clearInterval(pollInterval)
          ElMessage.error(statusRes.data.error_msg || '下载失败')
        }
      } catch (err) {
        clearInterval(pollInterval)
      }
    }, 2000)

    setTimeout(() => {
      if (activeTasks.value.find(t => t.id === res.data.id)?.status === 'completed') {
        clearInterval(pollInterval)
      }
    }, 600000) // 10分钟超时
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '提交下载任务失败')
  } finally {
    downloading.value = false
  }
}

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-left h3 {
  margin: 0;
  font-size: 18px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
}
.home-main {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 40px 24px;
}
.main-content {
  width: 100%;
  max-width: 800px;
}
.input-card {
  margin-bottom: 24px;
}
.video-info-section {
  margin-bottom: 24px;
}
</style>
```

- [ ] **Step 2: 创建 frontend/src/components/VideoCard.vue**

```vue
<template>
  <el-card class="video-card" shadow="hover">
    <div class="video-info">
      <div class="cover-wrapper">
        <img v-if="info.cover_url" :src="info.cover_url" class="video-cover" />
        <div v-else class="cover-placeholder">
          <el-icon :size="48"><VideoCamera /></el-icon>
        </div>
        <el-tag class="platform-tag" :type="platformType" effect="dark">
          {{ platformLabel }}
        </el-tag>
      </div>
      <div class="video-details">
        <h4 class="video-title">{{ info.title }}</h4>
        <div class="video-meta">
          <span class="meta-item">
            <el-icon><User /></el-icon>
            {{ info.author }}
          </span>
          <span class="meta-item">
            <el-icon><Timer /></el-icon>
            {{ formatDuration(info.duration) }}
          </span>
        </div>
        <div class="video-actions">
          <el-button
            type="primary"
            size="large"
            :loading="downloading"
            :icon="Download"
            @click="$emit('download')"
          >
            {{ downloading ? '正在提交...' : '下载无水印视频' }}
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { VideoCamera, User, Timer, Download } from '@element-plus/icons-vue'

const props = defineProps({
  info: { type: Object, required: true },
  downloading: { type: Boolean, default: false },
})

defineEmits(['download'])

const platformLabel = computed(() => {
  const map = { douyin: '抖音', bilibili: 'B站', xiaohongshu: '小红书' }
  return map[props.info.platform] || props.info.platform
})

const platformType = computed(() => {
  const map = { douyin: 'danger', bilibili: '', xiaohongshu: 'danger' }
  return map[props.info.platform] || 'info'
})

function formatDuration(seconds) {
  if (!seconds) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.video-info {
  display: flex;
  gap: 20px;
}
.cover-wrapper {
  position: relative;
  flex-shrink: 0;
  width: 200px;
  height: 140px;
  border-radius: 8px;
  overflow: hidden;
  background: #f0f2f5;
}
.video-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
}
.platform-tag {
  position: absolute;
  top: 8px;
  left: 8px;
}
.video-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.video-title {
  margin: 0;
  font-size: 16px;
  color: #303133;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.video-meta {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 13px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.video-actions {
  margin-top: 8px;
}
</style>
```

- [ ] **Step 3: 创建 frontend/src/components/DownloadProgress.vue**

```vue
<template>
  <el-card class="progress-card" shadow="hover">
    <template #header>
      <span>下载任务</span>
    </template>
    <div v-for="task in tasks" :key="task.id" class="task-item">
      <div class="task-info">
        <el-tag
          :type="task.platform === 'douyin' ? 'danger' : ''"
          size="small"
          effect="dark"
        >
          {{ task.platform === 'douyin' ? '抖音' : 'B站' }}
        </el-tag>
        <span class="task-title">{{ task.title || '加载中...' }}</span>
      </div>
      <div class="task-status">
        <el-tag v-if="task.status === 'pending'" type="info" size="small">排队中</el-tag>
        <el-tag v-else-if="task.status === 'parsing'" type="warning" size="small">解析中</el-tag>
        <el-tag v-else-if="task.status === 'downloading'" type="warning" size="small">下载中</el-tag>
        <el-tag v-else-if="task.status === 'processing'" type="warning" size="small">处理中</el-tag>
        <el-tag v-else-if="task.status === 'completed'" type="success" size="small">已完成</el-tag>
        <el-tag v-else-if="task.status === 'failed'" type="danger" size="small">失败</el-tag>
      </div>
      <el-progress
        v-if="task.status !== 'completed' && task.status !== 'failed'"
        :percentage="taskProgress(task.status)"
        :indeterminate="task.status === 'pending'"
        :stroke-width="6"
      />
    </div>
    <el-empty v-if="!tasks.length" description="暂无下载任务" :image-size="60" />
  </el-card>
</template>

<script setup>
defineProps({
  tasks: { type: Array, default: () => [] },
})

function taskProgress(status) {
  const map = {
    pending: 5,
    parsing: 15,
    downloading: 50,
    processing: 80,
    completed: 100,
    failed: 100,
  }
  return map[status] || 0
}
</script>

<style scoped>
.task-item {
  padding: 10px 0;
  border-bottom: 1px solid #f0f2f5;
}
.task-item:last-child {
  border-bottom: none;
}
.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.task-title {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-status {
  margin-bottom: 6px;
}
</style>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/Home.vue frontend/src/components/VideoCard.vue frontend/src/components/DownloadProgress.vue
git commit -m "feat: implement home page with video parsing and download"
```

### Task 15: 历史记录页和用户管理页

**Files:**
- Create: `frontend/src/views/History.vue`
- Create: `frontend/src/views/Users.vue`

- [ ] **Step 1: 创建 frontend/src/views/History.vue**

```vue
<template>
  <el-container class="page-container">
    <el-header class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/')" :icon="ArrowLeft" type="text">返回首页</el-button>
        <h3>下载历史</h3>
      </div>
    </el-header>
    <el-main>
      <el-card>
        <el-table :data="history" stripe v-loading="loading" empty-text="暂无下载记录">
          <el-table-column prop="platform" label="平台" width="80">
            <template #default="{ row }">
              <el-tag :type="row.platform === 'douyin' ? 'danger' : ''" size="small">
                {{ row.platform === 'douyin' ? '抖音' : 'B站' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="video_title" label="视频标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="video_author" label="作者" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'completed'" type="success" size="small">已完成</el-tag>
              <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
              <el-tag v-else type="warning" size="small">处理中</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'completed'"
                type="primary"
                size="small"
                @click="downloadFile(row)"
              >
                下载文件
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import api from '../api/index'

const history = ref([])
const loading = ref(false)

async function fetchHistory() {
  loading.value = true
  try {
    const res = await api.get('/video/history')
    history.value = res.data
  } catch (err) {
    // Silently fail, table will show empty
  } finally {
    loading.value = false
  }
}

function downloadFile(row) {
  const a = document.createElement('a')
  a.href = `/api/video/task/${row.id}/file`
  a.download = `${row.video_title || 'video'}.mp4`
  a.click()
}

onMounted(fetchHistory)
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: #f5f7fa;
}
.page-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h3 {
  margin: 0;
}
</style>
```

- [ ] **Step 2: 创建 frontend/src/views/Users.vue**

```vue
<template>
  <el-container class="page-container">
    <el-header class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/')" :icon="ArrowLeft" type="text">返回首页</el-button>
        <h3>用户管理</h3>
      </div>
      <el-button type="primary" @click="showAddDialog">添加用户</el-button>
    </el-header>
    <el-main>
      <el-card>
        <el-table :data="users" stripe v-loading="loading">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'warning' : ''" size="small">
                {{ row.role === 'admin' ? '管理员' : '成员' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-main>

    <!-- Add User Dialog -->
    <el-dialog v-model="dialogVisible" title="添加用户" width="400px">
      <el-form ref="formRef" :model="form" :rules="rules">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddUser">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api/index'
import { register } from '../api/auth'

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await api.get('/auth/users')
    users.value = res.data
  } catch (err) {
    // empty
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  form.username = ''
  form.password = ''
  dialogVisible.value = true
}

async function handleAddUser() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await register(form.username, form.password)
    ElMessage.success('用户添加成功')
    dialogVisible.value = false
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: #f5f7fa;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h3 {
  margin: 0;
}
</style>
```

- [ ] **Step 3: 在后端添加历史记录和用户列表 API**

更新 `backend/app/api/video.py` 添加历史记录端点：

```python
@router.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's download history."""
    from sqlalchemy import select
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
```

更新 `backend/app/api/auth.py` 添加用户管理端点（需要在文件顶部添加 `from ..utils.dependencies import get_current_user`）：

```python
@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/History.vue frontend/src/views/Users.vue backend/app/api/video.py backend/app/api/auth.py
git commit -m "feat: add history and user management pages with backend APIs"
```

---

## Phase 7: 部署配置

### Task 16: 最终部署配置

**Files:**
- Create: `README.md`
- Modify: `backend/app/config.py`

- [ ] **Step 1: 创建 README.md**

```markdown
# 视频下载助手

支持多平台视频无水印下载的 Web 应用。

## 支持平台

- 抖音 (Douyin)
- B站 (Bilibili)
- 小红书 (Xiaohongshu) —— 开发中

## 快速部署

### 前置要求

- Docker & Docker Compose
- 域名（可选，用于 HTTPS）

### 一键部署

\`\`\`bash
# 克隆代码
git clone <repo-url> && cd pachongtools

# 修改环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，修改 SECRET_KEY 等配置

# 启动所有服务
docker-compose up -d --build
\`\`\`

### 初始化管理员

\`\`\`bash
# 注册第一个用户
curl -X POST http://your-server/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# 手动设为 admin（进入 PostgreSQL）
docker-compose exec db psql -U postgres -d videocrawler \
  -c "UPDATE users SET role='admin' WHERE username='admin';"
\`\`\`

## 开发

\`\`\`bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev

# Celery Worker (另一个终端)
cd backend
celery -A app.celery_app worker --loglevel=info
\`\`\`
```

- [ ] **Step 2: 确认所有文件就位，最终验证**

Run:
```bash
cd d:/liyik/桌面/pachongtools
find . -type f | grep -v node_modules | grep -v __pycache__ | sort
```
Expected: 所有设计文档中定义的文件都存在。

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with deployment and development instructions"
```
