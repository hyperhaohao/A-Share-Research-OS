# Migration Guide（数据库迁移）

## 体系

- SQLAlchemy 2 声明模型（`app/storage/*_orm.py`）+ Alembic；
- 全量模型注册：`app/storage/all_models.py` —— **新增 ORM 必须在此 import**，
  否则 autogenerate 漏表（M23 曾因此产生空迁移，已修复并记录）；
- env.py：`render_as_batch=True`（SQLite 友好）；URL 取 `ASRO_DATABASE_URL`。

## 常用命令（backend/ 目录）

```bash
# 生成迁移（先确保 DB 在最新 head）
ASRO_DATABASE_URL=sqlite:///./asro_dev.db uv run alembic revision --autogenerate -m "..."

# 应用
ASRO_DATABASE_URL=sqlite:///./asro_dev.db uv run alembic upgrade head

# 回退一版
ASRO_DATABASE_URL=sqlite:///./asro_dev.db uv run alembic downgrade -1
```

## 版本历史

- `0f8802656fc2` initial schema（m4–m23 合并基线；25 表）
- 后续按里程碑增量。

> 注：早期按里程碑逐个生成的 m6–m23 迁移因 Windows 文件锁导致 `rm` 静默失败、
> autogenerate 无差异而成为空文件，已被合并基线替代（保留于 Git 历史 0f8802656fc2
> 之前）。当前链为单基线 + 增量。

## PostgreSQL

`ASRO_DATABASE_URL=postgresql+psycopg://...` 即可；SQLite 专用的 batch 模式
已全局开启，不会影响 PostgreSQL。
