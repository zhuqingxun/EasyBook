# FastAPI 项目最佳实践技术笔记

## 1. 项目结构

### 推荐的中型项目目录结构（模块功能组织方式）

```
my_fastapi_project/
├── .env                          # 环境变量配置
├── .env.example                  # 环境变量示例
├── pyproject.toml                # uv 项目配置
├── uv.lock                       # 依赖锁定文件
├── README.md
├── alembic/                      # 数据库迁移
│   ├── versions/
│   └── env.py
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── config.py                 # 配置管理（pydantic-settings）
│   ├── database.py               # 数据库连接配置
│   ├── dependencies.py           # 全局依赖注入
│   ├── middleware/               # 中间件
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   └── timing.py
│   ├── core/                     # 核心功能
│   │   ├── __init__.py
│   │   ├── security.py           # 认证/授权
│   │   └── logging_config.py     # 日志配置
│   ├── models/                   # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   └── book.py
│   ├── schemas/                  # Pydantic 模型（请求/响应）
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── book.py
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── deps.py               # 路由级依赖
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # 汇总所有 v1 路由
│   │       ├── users.py
│   │       ├── books.py
│   │       └── health.py
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── search_service.py     # Meilisearch 集成
│   ├── repositories/             # 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── user_repository.py
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       └── validators.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── api/
        └── v1/
            └── test_users.py
```

**推荐理由**：
- 按模块功能组织而非文件类型，适合大型单体应用
- 清晰的分层架构：API → Service → Repository → Model
- 便于扩展和维护

## 2. pyproject.toml 配置（uv + hatchling）

```toml
[project]
name = "my-fastapi-app"
version = "0.1.0"
description = "FastAPI 项目示例"
readme = "README.md"
requires-python = ">=3.12"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]

dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",               # PostgreSQL 异步驱动
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",      # 环境变量管理
    "alembic>=1.13.0",               # 数据库迁移
    "python-dotenv>=1.0.0",
    "slowapi>=0.1.9",                # API 限流
    "redis>=5.0.0",                  # 限流后端
    "meilisearch-python-sdk>=3.0.0", # 搜索引擎
    "python-multipart>=0.0.9",       # 表单数据支持
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",                 # FastAPI 测试客户端
    "ruff>=0.7.0",                   # Linter
    "mypy>=1.11.0",                  # 类型检查
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = []

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**使用 uv 常用命令**：
```bash
# 初始化项目
uv init --app

# 添加依赖
uv add fastapi[standard] sqlalchemy[asyncio] asyncpg

# 添加开发依赖
uv add --dev pytest pytest-asyncio

# 同步依赖
uv sync

# 运行应用
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest
```

## 3. 异步数据库访问

### 方案选择：SQLAlchemy 2.0+ Async + asyncpg

**推荐原因**：
- SQLAlchemy 2.0 完全支持异步操作
- asyncpg 是 PostgreSQL 最快的异步驱动
- 成熟的生态系统和 ORM 功能

### 数据库配置（`app/database.py`）

```python
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


# 创建异步引擎（应用启动时调用一次）
def get_async_engine() -> AsyncEngine:
    """
    创建异步数据库引擎，配置连接池参数

    连接池参数说明：
    - pool_size: 常驻连接数（默认 5），根据并发需求调整
    - max_overflow: 超出 pool_size 的额外连接数（默认 10）
    - pool_timeout: 获取连接的最大等待时间（秒）
    - pool_recycle: 连接回收时间（秒），防止数据库超时断开
    - pool_pre_ping: 每次使用前检查连接是否有效
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # 开发环境打印 SQL
        pool_size=10,         # 根据实际并发调整（推荐：CPU 核心数 * 2 + 1）
        max_overflow=20,      # 峰值流量时的额外连接
        pool_timeout=30,      # 等待连接超时时间
        pool_recycle=3600,    # 1 小时回收连接，防止数据库端超时
        pool_pre_ping=True,   # 每次使用前 ping 检查连接有效性
    )
    logger.info("Database engine created with async pool configuration")
    return engine


# 全局引擎实例（在 main.py 的 lifespan 中初始化）
engine: AsyncEngine | None = None

# 会话工厂（在引擎初始化后创建）
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    依赖注入函数：提供数据库会话

    用法：
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # 成功时自动提交
        except Exception:
            await session.rollback()  # 异常时回滚
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """应用启动时初始化数据库连接池"""
    global engine, async_session_maker

    engine = get_async_engine()
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # 提交后对象仍可访问属性
    )
    logger.info("Database connection pool initialized")


async def close_db() -> None:
    """应用关闭时释放数据库连接"""
    if engine:
        await engine.dispose()
        logger.info("Database connection pool disposed")
```

### ORM 模型示例（`app/models/user.py`）

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

    # 自动时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
```

## 4. PostgreSQL 连接池最佳实践

### 关键配置参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `pool_size` | `10-20` | 常驻连接数，建议设为 CPU 核心数 × 2 + 1 |
| `max_overflow` | `10-20` | 峰值流量时的额外连接，总连接 = pool_size + max_overflow |
| `pool_timeout` | `30` | 等待连接的超时时间（秒） |
| `pool_recycle` | `3600` | 连接回收时间（秒），防止数据库端超时 |
| `pool_pre_ping` | `True` | 每次使用前检查连接有效性，防止使用断开的连接 |

### 生产环境调优建议

1. **监控指标**：
   - 连接池使用率（pool_size / 活跃连接数）
   - 连接等待时间
   - 数据库 `max_connections` 设置

2. **计算公式**：
   ```
   pool_size = (CPU 核心数 × 2) + 磁盘数量
   max_overflow = pool_size
   数据库 max_connections >= (应用实例数 × (pool_size + max_overflow)) + 预留
   ```

3. **常见问题**：
   - 连接泄漏：确保使用 `async with` 或依赖注入自动关闭会话
   - 连接耗尽：调大 `pool_size` 或优化慢查询
   - 超时断开：设置 `pool_recycle` < 数据库 `wait_timeout`

## 5. Pydantic v2 模型最佳实践

### Schema 文件（`app/schemas/user.py`）

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# 基础模型（共享字段）
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)


# 创建请求（客户端 → 服务器）
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


# 更新请求（部分字段可选）
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=8, max_length=100)


# 响应模型（服务器 → 客户端，不含敏感信息）
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 配置
    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 模型读取（v1 的 orm_mode）
        json_schema_extra={    # 文档示例
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }
    )


# 数据库内部模型（含敏感字段，不用于 API）
class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 关键最佳实践

1. **模型分离原则**：
   - `UserBase`: 共享字段
   - `UserCreate`: 创建请求（含密码）
   - `UserUpdate`: 更新请求（字段可选）
   - `UserResponse`: API 响应（不含密码）
   - `UserInDB`: 内部使用（含 `hashed_password`）

2. **性能优化**：
   - 避免在路由中显式创建响应模型（FastAPI 会自动验证两次）
   - 直接返回 ORM 对象，让 `response_model` 处理序列化

3. **Pydantic v2 新特性**：
   - `model_config = ConfigDict()` 替代 v1 的 `class Config`
   - `from_attributes=True` 替代 `orm_mode=True`
   - 更好的性能和类型安全

## 6. CORS 配置

### 生产环境配置（`app/main.py`）

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="My API")

# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 从环境变量读取
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],  # 前端可读的响应头
    max_age=600,  # 预检请求缓存时间（秒）
)
```

### 环境变量配置（`.env`）

```env
# 开发环境
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# 生产环境
CORS_ORIGINS=["https://app.example.com", "https://www.example.com"]
```

### 配置类（`app/config.py`）

```python
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """支持从字符串解析 JSON 数组"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )
```

**安全注意事项**：
- ⛔ **禁止**在生产环境使用 `allow_origins=["*"]`
- ⛔ **禁止**同时设置 `allow_origins=["*"]` 和 `allow_credentials=True`（浏览器会拒绝）
- ✅ 明确列出所有允许的前端域名
- ✅ 使用 HTTPS 域名（生产环境）

## 7. 环境变量管理（pydantic-settings）

### 配置文件（`app/config.py`）

```python
import logging
from functools import lru_cache
from typing import List, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置（从环境变量加载）"""

    # 应用基础配置
    APP_NAME: str = "FastAPI App"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "production"

    # 数据库配置
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/dbname"
    )

    # Redis 配置（用于限流）
    REDIS_URL: str = "redis://localhost:6379/0"

    # Meilisearch 配置
    MEILISEARCH_URL: str = "http://localhost:7700"
    MEILISEARCH_API_KEY: str = ""

    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # JWT 配置
    SECRET_KEY: str = Field(min_length=32)  # 必须提供，至少 32 字符
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """支持从 JSON 字符串解析 CORS 域名列表"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """确保使用异步驱动"""
        if isinstance(v, str) and "postgresql://" in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",             # 从 .env 文件读取
        env_file_encoding="utf-8",
        case_sensitive=True,         # 环境变量大小写敏感
        extra="ignore",              # 忽略未定义的环境变量
    )


@lru_cache  # 单例模式：仅加载一次配置
def get_settings() -> Settings:
    """
    获取应用配置（全局单例）

    使用 @lru_cache 确保配置只加载一次，避免重复读取 .env 文件
    """
    settings = Settings()
    logger.info(f"Settings loaded for environment: {settings.ENVIRONMENT}")
    return settings


# 导出全局配置实例
settings = get_settings()
```

### 环境变量文件（`.env`）

```env
# 应用配置
APP_NAME="My FastAPI App"
DEBUG=true
ENVIRONMENT=development

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mydb

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# Meilisearch 配置
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your_master_key_here

# CORS 配置（JSON 数组格式）
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# JWT 配置
SECRET_KEY=your-super-secret-key-min-32-characters-long-please-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=logs/app.log
```

### 环境变量示例文件（`.env.example`）

```env
# 应用配置
APP_NAME="My FastAPI App"
DEBUG=false
ENVIRONMENT=production

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# Meilisearch 配置
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=change_me

# CORS 配置
CORS_ORIGINS=["https://app.example.com"]

# JWT 配置（⚠️ 生产环境务必修改）
SECRET_KEY=change_me_to_a_random_32_character_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 在路由中使用配置

```python
from fastapi import Depends
from app.config import Settings, get_settings

@app.get("/info")
async def app_info(settings: Settings = Depends(get_settings)):
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }
```

## 8. 日志配置

### 日志配置模块（`app/core/logging_config.py`）

```python
import logging
import sys
from pathlib import Path

from app.config import settings


def setup_logging() -> None:
    """
    配置应用日志系统（在 main.py 的 lifespan 中调用一次）

    功能：
    - 开发环境：控制台输出，带颜色格式
    - 生产环境：文件输出 + 控制台输出，JSON 格式（可选）
    - 统一 uvicorn 日志格式
    """
    # 创建日志目录
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # 日志格式
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    # 根 Logger 配置
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 控制台输出
            logging.StreamHandler(sys.stdout),
            # 文件输出
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    # 调整第三方库日志级别（避免过于冗长）
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={settings.LOG_LEVEL}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """获取模块 Logger（推荐用法：logger = get_logger(__name__)）"""
    return logging.getLogger(name)
```

### 在模块中使用日志

```python
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)  # 模块级 Logger

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    """获取用户列表"""
    logger.info("Fetching all users")

    try:
        # 数据库操作
        result = await db.execute(select(User))
        users = result.scalars().all()

        logger.info(f"Successfully fetched {len(users)} users")
        return users

    except Exception as e:
        logger.exception(f"Failed to fetch users: {e}")  # 自动记录堆栈
        raise
```

### 主应用中初始化日志（`app/main.py`）

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging_config import setup_logging
from app.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    setup_logging()  # 必须在最开始配置日志
    await init_db()

    yield

    # 关闭时
    await close_db()


app = FastAPI(lifespan=lifespan)
```

### 日志级别使用规范

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| `DEBUG` | 调试细节，生产环境关闭 | `logger.debug(f"Query params: {params}")` |
| `INFO` | 关键业务流程 | `logger.info("User registered successfully")` |
| `WARNING` | 可自行处理的异常 | `logger.warning("Rate limit exceeded, retrying")` |
| `ERROR` | 操作失败但不影响系统 | `logger.error(f"Failed to send email: {e}")` |
| `CRITICAL` | 系统级故障 | `logger.critical("Database connection lost")` |

**异常日志最佳实践**：
```python
try:
    result = await external_api_call()
except HTTPException as e:
    logger.exception(  # 自动包含堆栈信息
        f"External API call failed: "
        f"endpoint={endpoint}, status={e.status_code}"
    )
    raise
```

## 9. API 限流（SlowAPI）

### 安装依赖

```bash
uv add slowapi redis
```

### 限流配置（`app/main.py`）

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


# 创建限流器（使用 Redis 后端）
limiter = Limiter(
    key_func=get_remote_address,  # 按 IP 地址限流
    storage_uri=settings.REDIS_URL,  # 生产环境使用 Redis
    default_limits=["200/minute"],   # 全局默认限制
    strategy="fixed-window",         # 固定窗口策略
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("Starting up application")
    yield
    logger.info("Shutting down application")


app = FastAPI(lifespan=lifespan)

# 添加限流中间件
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

### 在路由中应用限流

```python
from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.main import limiter

router = APIRouter()


@router.get("/limited")
@limiter.limit("5/minute")  # 每分钟最多 5 次请求
async def limited_endpoint(request: Request):
    """限流测试端点"""
    return {"message": "This endpoint is rate-limited"}


@router.post("/login")
@limiter.limit("10/hour")  # 登录接口严格限制
async def login(request: Request):
    """登录接口（防止暴力破解）"""
    return {"message": "Login endpoint"}


# 动态限流（根据用户身份）
def get_user_key(request: Request) -> str:
    """根据用户 ID 限流（需要认证）"""
    user_id = request.state.user.id if hasattr(request.state, "user") else "anonymous"
    return f"user:{user_id}"


@router.get("/premium")
@limiter.limit("100/minute", key_func=get_user_key)  # VIP 用户更高限额
async def premium_endpoint(request: Request):
    """高级功能端点"""
    return {"message": "Premium feature"}
```

### 自定义限流响应

```python
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """自定义限流错误响应"""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too Many Requests",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.detail,  # 返回重试时间
        },
        headers={
            "Retry-After": str(exc.detail),
            "X-RateLimit-Limit": str(exc.limit.limit),
            "X-RateLimit-Remaining": "0",
        },
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
```

### 环境变量配置

```env
# Redis 配置（限流后端）
REDIS_URL=redis://localhost:6379/0
```

**生产环境建议**：
- 使用 Redis 作为存储后端（支持分布式部署）
- 不同端点设置不同限流策略（登录 < 查询 < 写入）
- 返回 `Retry-After` 和 `X-RateLimit-*` 响应头
- 监控限流触发率，调整阈值

## 10. 健康检查端点

### 健康检查路由（`app/api/v1/health.py`）

```python
import logging
from typing import Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Kubernetes liveness probe - 检查应用进程是否存活",
)
async def liveness() -> Dict[str, str]:
    """
    存活探针（Liveness Probe）

    用途：Kubernetes 用此判断容器是否需要重启
    检查内容：仅检查应用进程是否响应（不检查外部依赖）
    失败行为：Kubernetes 会重启 Pod
    """
    return {"status": "ok"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Kubernetes readiness probe - 检查应用是否可接收流量",
)
async def readiness(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    就绪探针（Readiness Probe）

    用途：Kubernetes 用此判断是否将流量路由到此 Pod
    检查内容：检查所有外部依赖（数据库、Redis、Meilisearch 等）
    失败行为：Pod 从 Service 负载均衡中移除，但不会重启
    """
    checks = {
        "status": "ok",
        "database": "unhealthy",
    }

    # 检查数据库连接
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = "healthy"
        logger.debug("Database health check passed")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["status"] = "degraded"

    # 可以添加更多检查（Redis、Meilisearch 等）
    # try:
    #     await redis_client.ping()
    #     checks["redis"] = "healthy"
    # except Exception as e:
    #     logger.error(f"Redis health check failed: {e}")
    #     checks["redis"] = "unhealthy"
    #     checks["status"] = "degraded"

    # 如果任何依赖不健康，返回 503
    if checks["status"] != "ok":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=checks,
        )

    return checks


@router.get(
    "/health/startup",
    status_code=status.HTTP_200_OK,
    summary="Startup Probe",
    description="Kubernetes startup probe - 检查应用是否已启动完成",
)
async def startup() -> Dict[str, str]:
    """
    启动探针（Startup Probe）

    用途：Kubernetes 用此判断应用是否已完成初始化
    检查内容：检查应用启动任务是否完成（如数据库迁移、缓存预热）
    失败行为：在超时前持续检查，超时后重启 Pod
    """
    # 简单实现：检查应用是否响应即可
    # 复杂场景：可以检查数据迁移状态、缓存预热完成等
    return {"status": "ok"}
```

### Kubernetes 配置示例（`deployment.yaml`）

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
      - name: app
        image: my-fastapi-app:latest
        ports:
        - containerPort: 8000

        # 启动探针（应用启动时检查）
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30  # 最多等待 150 秒（5s × 30）

        # 存活探针（运行时检查进程）
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        # 就绪探针（检查能否接收流量）
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

**关键区别**：

| 探针类型 | 检查内容 | 失败行为 | 使用场景 |
|---------|---------|---------|---------|
| **Liveness** | 进程是否存活 | 重启容器 | 检测死锁、无限循环 |
| **Readiness** | 是否可接收流量 | 移出负载均衡 | 检查依赖服务（数据库、缓存） |
| **Startup** | 是否启动完成 | 重启容器 | 慢启动应用（避免被 liveness 误杀） |

## 11. Docker Compose 配置

### `docker-compose.yml`

```yaml
version: "3.8"

services:
  # FastAPI 应用
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fastapi-app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/mydb
      - REDIS_URL=redis://redis:6379/0
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_API_KEY=${MEILISEARCH_MASTER_KEY}
      - ENVIRONMENT=development
      - DEBUG=true
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      meilisearch:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs  # 日志持久化
    networks:
      - app-network
    restart: unless-stopped

  # PostgreSQL 数据库
  postgres:
    image: postgres:16-alpine
    container_name: postgres-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped

  # Redis（用于限流和缓存）
  redis:
    image: redis:7-alpine
    container_name: redis-cache
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - app-network
    restart: unless-stopped

  # Meilisearch（搜索引擎）
  meilisearch:
    image: getmeili/meilisearch:v1.10
    container_name: meilisearch
    environment:
      MEILI_MASTER_KEY: ${MEILISEARCH_MASTER_KEY:-your_master_key_here}
      MEILI_ENV: development  # 生产环境改为 production
      MEILI_NO_ANALYTICS: true
    ports:
      - "7700:7700"
    volumes:
      - meilisearch-data:/meili_data
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--spider", "http://localhost:7700/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped

  # pgAdmin（可选，数据库管理界面）
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    networks:
      - app-network
    restart: unless-stopped
    profiles:
      - tools  # 仅在 --profile tools 时启动

volumes:
  postgres-data:
  redis-data:
  meilisearch-data:

networks:
  app-network:
    driver: bridge
```

### Dockerfile

```dockerfile
# 多阶段构建，减小镜像体积
FROM python:3.12-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖（使用 uv）
RUN uv sync --frozen --no-dev

# 运行阶段
FROM python:3.12-slim

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 从 builder 复制依赖
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建日志目录
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# 切换到非 root 用户
USER appuser

# 设置环境变量
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 启动命令

```bash
# 启动所有服务
docker compose up -d

# 仅启动核心服务（不含 pgAdmin）
docker compose up -d

# 启动并包含工具（pgAdmin）
docker compose --profile tools up -d

# 查看日志
docker compose logs -f app

# 重启应用
docker compose restart app

# 停止所有服务
docker compose down

# 停止并删除数据卷（⚠️ 会删除数据）
docker compose down -v
```

### `.env` 文件（Docker Compose 使用）

```env
# Meilisearch 主密钥（必须设置）
MEILISEARCH_MASTER_KEY=your_super_secret_master_key_min_16_chars
```

**生产环境建议**：
- 使用 Docker Compose 的 `secrets` 管理敏感信息
- 为每个服务设置资源限制（`deploy.resources`）
- 使用 `restart: always` 自动重启失败容器
- 配置日志驱动和轮转策略
- 使用 Traefik 或 Nginx 反向代理

---

## 完整应用示例（`app/main.py`）

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.logging_config import setup_logging
from app.database import init_db, close_db
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


# 限流器
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=["200/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    setup_logging()
    logger.info("Application starting up")
    await init_db()

    yield

    # 关闭时
    logger.info("Application shutting down")
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI 最佳实践示例项目",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # 生产环境关闭文档
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=600,
)

# 添加限流中间件
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to FastAPI",
        "docs": "/docs",
        "health": "/api/v1/health/live",
    }
```

### 路由汇总（`app/api/v1/router.py`）

```python
from fastapi import APIRouter

from app.api.v1 import users, books, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(books.router, prefix="/books", tags=["Books"])
```

---

## 参考资源

### 官方文档
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [uv 官方文档](https://docs.astral.sh/uv/)
- [Pydantic v2 文档](https://docs.pydantic.dev/latest/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)

### 最佳实践
- [GitHub - FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [FastAPI Project Structure Best Practices - DEV Community](https://dev.to/mohammad222pr/structuring-a-fastapi-project-best-practices-53l6)
- [Using uv with FastAPI | uv](https://docs.astral.sh/uv/guides/integration/fastapi/)
- [Building High-Performance Async APIs with FastAPI, SQLAlchemy 2.0, and Asyncpg | Leapcell](https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg)

### 工具库文档
- [SlowAPI Documentation](https://slowapi.readthedocs.io/)
- [Meilisearch Documentation](https://www.meilisearch.com/docs)
- [Settings and Environment Variables - FastAPI](https://fastapi.tiangolo.com/advanced/settings/)
- [How to Get Started with Logging in FastAPI | Better Stack Community](https://betterstack.com/community/guides/logging/logging-with-fastapi/)

### Docker 和部署
- [Using Meilisearch with Docker - Meilisearch Documentation](https://www.meilisearch.com/docs/guides/docker)
- [Dockerize FastAPI with PostgreSQL: A Complete Guide | Kite Metric](https://kitemetric.com/blogs/dockerizing-a-fastapi-project-with-postgresql-a-comprehensive-guide)

---

## 总结

本文档涵盖了 FastAPI 项目的核心最佳实践：

1. ✅ **项目结构**：模块功能组织方式，适合中大型应用
2. ✅ **包管理**：使用 uv 替代 pip，更快的依赖解析
3. ✅ **数据库**：SQLAlchemy 2.0 异步 + asyncpg，连接池优化
4. ✅ **数据验证**：Pydantic v2 模型分离，性能优化
5. ✅ **安全配置**：CORS、环境变量、JWT（待补充）
6. ✅ **日志系统**：标准化日志配置，生产环境可观测
7. ✅ **限流保护**：SlowAPI + Redis，防止 API 滥用
8. ✅ **健康检查**：Kubernetes 三种探针实现
9. ✅ **容器化**：Docker Compose 编排多服务

**下一步扩展方向**：
- 认证授权（OAuth2 + JWT）
- 后台任务（Celery + Redis）
- 缓存策略（Redis 缓存层）
- API 版本管理
- 性能监控（Prometheus + Grafana）
- 自动化测试（pytest + httpx）
