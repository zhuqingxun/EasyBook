FROM python:3.12-slim

WORKDIR /app

# 关键：禁用 Python 输出缓冲，确保日志立即可见（Docker/Zeabur 环境必须）
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 先复制依赖文件，利用 Docker 缓存
COPY pyproject.toml uv.lock* ./

# 安装依赖
RUN uv sync --frozen --no-dev

# 复制应用代码
COPY app/ ./app/
COPY etl/ ./etl/

EXPOSE 8080

CMD uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level info
