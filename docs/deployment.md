# Deployment（任务书 §17/§82）

## Docker Compose（推荐）

```bash
cp .env.example .env   # 按需修改
docker compose up --build
```

- frontend: http://localhost:8080（nginx，静态 + /api 反代 + SSE 透传）
- backend:  http://localhost:8000（健康检查 `/api/v1/health`，容器 healthcheck）
- 数据卷 `backend_data` 持久化 SQLite 文件；生产切 PostgreSQL 见下。

> 网络说明：若 auth.docker.io 不可达（国内网络常见），先从镜像源拉取基础镜像
> 并本地 retag（如 `docker pull docker.m.daocloud.io/library/python:3.11-slim &&
> docker tag docker.m.daocloud.io/library/python:3.11-slim python:3.11-slim`，
> node/nginx 同理），再 `docker compose build` —— 构建将直接使用本地基础镜像。

## 后端配置（backend/app/config.py）

| 变量 | 默认 | 说明 |
|------|------|------|
| ASRO_DATABASE_URL | sqlite:///./asro_dev.db | 生产建议 PostgreSQL |
| ASRO_CORS_ORIGINS | localhost:5173 | 公网必须收敛到真实前端 origin |
| ASRO_DEBUG | false | 生产保持 false |

## 数据库迁移

```bash
cd backend && ASRO_DATABASE_URL=... uv run alembic upgrade head
```

后端容器启动时自动执行 `alembic upgrade head`；模型注册表见
`app/storage/all_models.py`（新增 ORM 必须在此 import，否则 autogenerate 漏表）。

## 升级

1. `git pull`；
2. `docker compose build`；
3. `docker compose up -d`（迁移自动执行；SQLite 升级前先 backup，见 backup-restore.md）。

## PDF 导出说明

Markdown 与 HTML 报告已可用（`GET /api/v1/reports/{id}/pdf`）；PDF 由 reportlab
以内置 Adobe CJK 字体（STSong-Light）生成，浅色主题，内容与 HTML 一致。
