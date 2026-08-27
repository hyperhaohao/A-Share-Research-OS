# Security Review（任务书 §85）

> 日期：2026-08-28（M28 安全复查）。

## 1. XSS / 不可信内容

| 面 | 措施 |
|----|------|
| 报告 HTML | `ReportRenderer.render_html` 对全部文本经 `html.escape` 输出；引用节点仅注入服务端生成的 evidence id（正则白名单格式） |
| React 渲染 | 全部用户/API 文本经 JSX 默认转义；唯一 `dangerouslySetInnerHTML`（报告正文）内容为服务端转义后的产物 |
| 外部新闻/研报文本 | 按不可信输入处理：进入 Evidence 原文字段后仅在转义管道中输出，永不注入 HTML |

## 2. 注入

- 数据访问全部经 SQLAlchemy ORM 参数化查询；无字符串拼接 SQL。
- API 输入经 Pydantic 校验（类型/长度/枚举/正则）。

## 3. 认证与密钥

- API Key 不入库：数据 provider（腾讯行情）无需密钥；未来需密钥的 provider 一律从环境变量读取（`ASRO_` 前缀 settings）。
- `.env` 已 gitignore；仓库无明文密钥。
- 首版为单机/内网研究工具：API 未启用认证（公网部署必须显式配置 auth/CORS/trusted-hosts 后方可暴露，见下）。

## 4. CORS / 部署边界

- CORS 默认仅允许开发前端 origin（`localhost:5173`/`127.0.0.1:5173`）；
- 公网部署前必须：收敛 `ASRO_CORS_ORIGINS`、启用反向代理 TLS、增加 API 认证层（M29 部署文档说明）。

## 5. 数据库

- 开发 SQLite（WAL + 外键 pragma）；生产 PostgreSQL；
- 迁移经 Alembic 管理（`backend/alembic/versions/`），autogenerate 以 `app/storage/all_models.py` 注册全量模型。

## 6. 已知限制

- 无登录/角色体系（首版单用户定位）；
- SSE 流无认证（与上同）；
- 节假日交易日历未接入（预测 due 用周末近似）。
