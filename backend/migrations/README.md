# 数据库迁移

数据库结构只能通过 Alembic 迁移演进，FastAPI 启动时不会创建或修改表。

迁移环境会在内部将现有 psycopg 3 的 PostgreSQL URL 转为 SQLAlchemy 所需的 `postgresql+psycopg://` 方言；应用的 `DATABASE_URL` 不需要改写。

在 `backend/` 目录中执行：

```powershell
.\.venv\Scripts\alembic.exe -c alembic.ini upgrade head
```

旧版本如果已经由 FastAPI 启动逻辑创建了认证表，先确认结构与 `20260720_0001` 一致，再执行：

```powershell
.\.venv\Scripts\alembic.exe -c alembic.ini stamp 20260720_0001
```

`stamp` 只记录当前迁移版本，不会执行 SQL；不要在空数据库上使用它。
