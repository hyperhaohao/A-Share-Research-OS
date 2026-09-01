"""Entity Dictionary 与主体偷换检测（F4，第三轮整改任务书 §7.3 P1-A）.

实体词典至少覆盖（§7.3）：上市公司 / 控股股东 / 实际控制人 / 集团公司 /
子公司 / 同行业公司 / 监管机构 / 地方国资主体。

核心语义（§7.3 反例）：

    Evidence:  中国稀土集团正在研究资产整合方案
    Statement: 中国稀土股份正在筹划重大资产重组

不得仅因词面重叠（「中国稀土」）而通过 —— 两者是不同法人主体
（集团公司 ≠ 上市公司）。

机制（确定性、无 LLM、可审计）：
  1. ENTITY_ENTRIES 种子词典（类型 + 别名 + 关联标的）；
  2. resolve_entities(text)：最长别名匹配 → [(entity, alias)]；
  3. subject_swap_verdict(statement, evidence_text)：
     - statement 与 evidence 解析到不同 canonical 实体，且两实体同属
       一个 CONFUSABLE 组（名称互为前缀/别名重叠）→ uncertain
       `subject_entity_mismatch:<A>|<B>`；
     - statement 命中实体而 evidence 只命中其混淆对象 → 同上；
     - 其余情形保持 ok（保守，避免第一阶段误报回潮——§22.1 教训）。

reason code 机器可读（§7.4）：subject_entity_mismatch / subject_unverifiable。
词典可扩展：种子只含通用监管机构 + 000831 黄金链；新标的随
Instrument Registry 与后续关系源接入登记（reference: entity_dictionary.extend）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 实体类型（§7.3 至少覆盖）
ET_LISTED_COMPANY = "listed_company"
ET_HOLDING_SHAREHOLDER = "holding_shareholder"
ET_ACTUAL_CONTROLLER = "actual_controller"
ET_GROUP_COMPANY = "group_company"
ET_SUBSIDIARY = "subsidiary"
ET_PEER_COMPANY = "peer_company"
ET_REGULATOR = "regulator"
ET_LOCAL_SOE = "local_soe"


@dataclass(frozen=True)
class EntityEntry:
    canonical_name: str
    entity_type: str
    aliases: tuple[str, ...] = ()
    instrument_ids: tuple[str, ...] = ()
    note: str = ""


# ── 种子词典（通用 + 黄金场景 000831 链；结构对任何标的开放） ─────────────────

ENTITY_ENTRIES: tuple[EntityEntry, ...] = (
    # 监管机构（通用）
    EntityEntry("中国证券监督管理委员会", ET_REGULATOR, ("证监会", "中国证监会", "CSRC")),
    EntityEntry("国务院国有资产监督管理委员会", ET_REGULATOR, ("国资委", "国务院国资委", "SASAC")),
    EntityEntry("工业和信息化部", ET_REGULATOR, ("工信部",)),
    EntityEntry("国家发展和改革委员会", ET_REGULATOR, ("发改委", "国家发改委")),
    # 黄金链 000831：上市公司
    EntityEntry(
        "中国稀土集团资源股份有限公司", ET_LISTED_COMPANY,
        ("中国稀土", "中国稀土股份", "中国稀土股份有限公司"),
        instrument_ids=("SZSE:000831",),
        note="深市上市公司（简称「中国稀土」）",
    ),
    # 黄金链 000831：集团公司（与上市公司同名前缀 —— 主体偷换高危对）
    EntityEntry(
        "中国稀土集团有限公司", ET_GROUP_COMPANY,
        ("中国稀土集团", "稀土集团"),
        note="中国稀土集团资源股份有限公司的控股股东方（集团公司）",
    ),
    # 黄金链 000831：控股股东（地方国资）
    EntityEntry(
        "广东省广晟控股集团有限公司", ET_HOLDING_SHAREHOLDER,
        ("广晟控股集团", "广晟控股", "广晟"),
        note="持股中国稀土 9.48% 的股东（地方国资主体）",
    ),
)

# ── 别名索引（最长匹配优先） ──────────────────────────────────────────────────

_ALIAS_INDEX: dict[str, EntityEntry] = {}
for _e in ENTITY_ENTRIES:
    for _a in (_e.canonical_name, *_e.aliases):
        _ALIAS_INDEX[_a] = _e


def _sorted_aliases() -> tuple[str, ...]:
    """按别名长度降序（最长匹配优先，防止「中国稀土」吞掉「中国稀土集团」）。"""
    return tuple(sorted(_ALIAS_INDEX.keys(), key=len, reverse=True))


def resolve_entities(text: str) -> list[tuple[EntityEntry, str]]:
    """解析文本中的词典实体（最长别名匹配，去重）。"""
    if not text:
        return []
    found: list[tuple[EntityEntry, str]] = []
    seen: set[str] = set()
    consumed: list[tuple[int, int]] = []  # 已匹配区间，避免子串重复命中
    for alias in _sorted_aliases():
        idx = text.find(alias)
        while idx != -1:
            span = (idx, idx + len(alias))
            if any(s < span[1] and span[0] < e for s, e in consumed):
                idx = text.find(alias, idx + 1)
                continue
            entry = _ALIAS_INDEX[alias]
            if entry.canonical_name not in seen:
                found.append((entry, alias))
                seen.add(entry.canonical_name)
            consumed.append(span)
            break
        # 继续下一个别名
    return found


def _confusable(a: EntityEntry, b: EntityEntry) -> bool:
    """两实体是否为词面易混淆对（不同法人主体但名称重叠）。"""
    if a.canonical_name == b.canonical_name:
        return False
    names_a = {a.canonical_name, *a.aliases}
    names_b = {b.canonical_name, *b.aliases}
    for x in names_a:
        for y in names_b:
            if x in y or y in x:
                return True
    return False


def subject_swap_verdict(statement: str, evidence_text: str) -> tuple[str, str]:
    """主体偷换检测（§7.3）。

    Returns:
        ("ok", "") — 未检测到主体问题；
        ("uncertain", reason_code) — 主体不一致/不可核实（走人工审查）。
    """
    stmt_entities = resolve_entities(statement)
    ev_entities = resolve_entities(evidence_text)
    if not stmt_entities or not ev_entities:
        # statement 主体不在词典或 evidence 无实体 → 保守 ok
        #（避免第一阶段误报回潮；词典扩展后自动增强）
        return "ok", ""

    stmt_canonical = {e.canonical_name for e, _ in stmt_entities}
    ev_canonical = {e.canonical_name for e, _ in ev_entities}

    # 1) statement 实体在 evidence 中有直接命中 → 主体一致
    if stmt_canonical & ev_canonical:
        return "ok", ""

    # 2) 不同 canonical 实体 + 混淆对 → 主体偷换（uncertain，人工审查）
    for se, _ in stmt_entities:
        for ee, _ in ev_entities:
            if _confusable(se, ee):
                return (
                    "uncertain",
                    f"subject_entity_mismatch:{se.canonical_name}({se.entity_type})"
                    f"|{ee.canonical_name}({ee.entity_type})",
                )

    # 3) 完全无关实体并存 → 不因词典缺失误报
    return "ok", ""


def extend(entries: list[EntityEntry]) -> None:
    """运行时扩展词典（关系源接入后的登记入口）。"""
    global ENTITY_ENTRIES
    existing = {e.canonical_name for e in ENTITY_ENTRIES}
    new = tuple(e for e in entries if e.canonical_name not in existing)
    if not new:
        return
    ENTITY_ENTRIES = ENTITY_ENTRIES + new
    _ALIAS_INDEX.clear()
    for _e in ENTITY_ENTRIES:
        for _a in (_e.canonical_name, *_e.aliases):
            _ALIAS_INDEX[_a] = _e
