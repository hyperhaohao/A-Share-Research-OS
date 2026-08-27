# Backup / Restore（任务书 §83）

## 备份内容

1. 数据库（全部研究事实：evidence/snapshots/claims/theses/reports/versions/…）
2. 配置（`.env`）
3. 代码与迁移在 Git 中（不属于备份范围）

## 脚本

```bash
# 备份（WAL checkpoint 后拷贝，保证一致性）
scripts/backup.sh [输出目录]        # 默认 ./backups

# 恢复（拷回 + integrity_check）
scripts/restore.sh backups/asro-<时间戳>.db
```

环境变量 `ASRO_DB_FILE` 覆盖数据库路径（默认 `./asro_dev.db`）。

## 演练记录（2026-08-28）

```text
1. scripts/backup.sh → backups/asro-20260828-053514.db（integrity ok）
2. restore.sh → 回写 asro_dev.db
3. 校验：26 表（25 schema + alembic_version）全部存在
4. 抽查：evidence_records / research_tasks / watchlist 结构完整
结论：RESTORE DRILL PASS
```

## PostgreSQL 部署的备份

`pg_dump` / `pg_restore` 替换上述脚本；版本兼容性：恢复目标 PostgreSQL 版本
不得低于备份源；恢复后执行 `alembic current` 核对迁移版本。
