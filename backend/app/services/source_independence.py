"""Source Independence（F4，第三轮整改任务书 §7.2 P1-A）.

两个 Evidence 只有在来源链独立时才能计为两份 corroboration。
「>=2 T2/T3」必须指 >=2 independent source groups，不是两行 Evidence。

独立性判定覆盖（§7.2）：
  - 同一篇稿件不同站点转载      → content_hash / 规范化正文哈希 相同；
  - 同一通讯社稿件              → source_group 相同；
  - 同一公告的多个镜像页        → canonical_url / origin_url 相同；
  - 标题变化但正文 hash 高相似  → 规范化正文哈希（去标点/空白/大小写）；
  - 二次报道引用同一个原始来源  → original_source 相同。

字段最低要求（§7.2，由迁移 d3e4f5a6b7c8 提供）：
  publisher / origin_url / canonical_url / source_group / original_source /
  content_hash / published_at。历史行字段缺失时按「仅 content_hash 可判」
  降级 —— 降级状态显式披露（degraded_fields），不冒充完整判定。

输出 reason code 机器可读（§7.4）：
  satisfied / insufficient_independent_sources / degraded_fields。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.extraction import normalize_text


def _normalized_body_hash(title: str | None, summary: str | None) -> str | None:
    # 正文哈希刻意不含标题：规则 2 的目标正是「标题变化但正文高相似」的转载
    body = normalize_text(summary or "")
    if not body:
        return None
    import hashlib

    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass
class IndependenceGroup:
    members: list[str]
    representative_fields: dict = field(default_factory=dict)


def independence_groups(rows: list) -> list[IndependenceGroup]:
    """把证据行按来源链合并为独立性组（Union-Find，规则可审计）。

    rows: EvidenceORM 行（或提供同名字段的对象）。
    返回组列表；同组 = 不独立。
    """
    n = len(rows)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    body_hashes = [
        _normalized_body_hash(getattr(r, "title", None), getattr(r, "summary", None))
        for r in rows
    ]

    for i in range(n):
        for j in range(i + 1, n):
            a, b = rows[i], rows[j]
            # 规则 1：同一篇稿件（内容哈希一致）
            if a.content_hash and a.content_hash == b.content_hash:
                union(i, j)
                continue
            # 规则 2：标题变化但正文高相似（规范化正文哈希一致）
            if (
                body_hashes[i]
                and body_hashes[i] == body_hashes[j]
                and (getattr(a, "source", "") != getattr(b, "source", "") or a.evidence_id == b.evidence_id)
            ):
                union(i, j)
                continue
            # 规则 3：同一公告的多个镜像页
            ca = getattr(a, "canonical_url", None)
            cb = getattr(b, "canonical_url", None)
            oa = getattr(a, "source_url", None)
            ob = getattr(b, "source_url", None)
            if (ca and ca in (cb, ob)) or (cb and cb in (ca, oa)) or (
                oa and oa == ob and ca and cb
            ):
                union(i, j)
                continue
            # 规则 4：同一原始文档（同一公告 document id）
            da = getattr(a, "source_document_id", None)
            db = getattr(b, "source_document_id", None)
            if da and da == db:
                union(i, j)
                continue
            # 规则 5：二次报道引用同一个原始来源
            sa = getattr(a, "original_source", None)
            sb = getattr(b, "original_source", None)
            if sa and sa == sb:
                union(i, j)
                continue
            # 规则 6：同一通讯社/集团稿件（source_group 相同）
            ga = getattr(a, "source_group", None)
            gb = getattr(b, "source_group", None)
            if ga and ga == gb:
                union(i, j)
                continue

    groups: dict[int, list[str]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(rows[i].evidence_id)
    return [IndependenceGroup(members=m) for m in groups.values()]


def independent_group_count(rows: list) -> int:
    return len(independence_groups(rows))


def corroboration_check(
    rows: list, *, required_groups: int = 2
) -> dict:
    """「>=N 份独立来源」裁决（§7.2：组数 ≠ 行数）。

    返回：
      {
        "satisfied": bool,
        "independent_groups": int,
        "evidence_rows": int,
        "groups": [[evidence_id, ...], ...],
        "reason_code": satisfied | insufficient_independent_sources | degraded_fields,
      }
    """
    groups = independence_groups(rows)
    n_rows = len(rows)
    # 降级判定：所有行都缺独立性事实字段（publisher/source_group/urls/
    # original_source/document_id）→ 仅凭内容哈希无法确认「真独立」
    # （改写通稿无法由内容区分），裁决降级披露，不冒充通过（§7.4）。
    def _has_provenance(r) -> bool:
        return bool(
            getattr(r, "publisher", None)
            or getattr(r, "source_group", None)
            or getattr(r, "canonical_url", None)
            or getattr(r, "original_source", None)
            or getattr(r, "source_document_id", None)
        )

    degraded = not all(_has_provenance(r) for r in rows)
    satisfied = len(groups) >= required_groups
    if satisfied and degraded:
        # 内容上互不相同，但缺 provenance 字段 → 独立性不可确认
        reason = "degraded_fields"
        satisfied = False
    elif satisfied:
        reason = "satisfied"
    else:
        reason = "insufficient_independent_sources"
    return {
        "satisfied": satisfied,
        "independent_groups": len(groups),
        "evidence_rows": n_rows,
        "groups": [g.members for g in groups],
        "reason_code": reason,
    }
