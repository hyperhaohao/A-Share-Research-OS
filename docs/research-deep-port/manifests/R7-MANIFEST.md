# R7-MANIFEST — Research Memory

```text
donor basis:      98f1398（REFERENCE_ONLY：memories/ per-agent staging/晋升门 语义 → 行为适配）
backend:
  - app/application/memory.py + research_memories 表（migration a7b8c9d0e1f3）：
    七类（company/industry/event_playbook/research_method/known_failure/
    research_checklist/user_preference）+ scope（instrument/industry/
    event_type/intent/tags）+ version + status
  - 晋升门：create → candidate（不自动 active）；promote candidate→active→
    retired（禁跳级）；更新内容 = version+1
  - from_experience：仅 APPROVED 卡片可转 candidate（未批准 422），
    源 experience + artifact 引用保留
  - GET /memories 检索：type/scope/q（title+content+tags 匹配）
  - Memory≠Evidence 结构锁死：条目字段无 authority/fact_status
    （测试断言锁定，方案 §13.4）
deviations:       donor per-agent 隔离/FTS5 检索：ASRO 用 SQLite LIKE 起步
  （语料量级小）；FTS5/向量检索留待后续（manifest 如实登记）
tests:            tests/test_r7_memory.py 3/3；全量 backend exit 0；E2E 30/30
next: R8 Research Inbox / Thesis Diff
```
