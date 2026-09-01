"""Current Thesis 唯一选择器（F1，第二轮整改 P0-A1）.

禁止 select(ThesisORM).where(instrument_id==...).first()。
规则（方案第二轮 §5）：
  1. meta_json.is_current == true 的最新行；
  2. 无 is_current 时回退 created_at 最新（legacy fallback，显式记录）；
  3. 同一 instrument_id 原则上只能有一个 Current Thesis。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.research_orm import ThesisORM


def get_current_thesis(
    session: Session,
    instrument_id: str,
) -> ThesisORM | None:
    """返回该标的的 Current Thesis（唯一）。

    优先级：
      1. meta_json 含 is_current=true 的最新 created_at 行
      2. 无 is_current 标记 → created_at 最新行（legacy fallback）
    """
    rows = session.scalars(
        select(ThesisORM)
        .where(ThesisORM.instrument_id == instrument_id)
        .order_by(ThesisORM.created_at.desc())
        .limit(30)
    ).all()
    if not rows:
        return None

    # 优先：meta.is_current == true
    for r in rows:
        meta = r.meta_json or {}
        if meta.get("is_current"):
            return r

    # legacy fallback: created_at 最新
    return rows[0]


def demote_other_currents(session: Session, instrument_id: str, keep_thesis_id: str) -> int:
    """将同一 instrument 下除 keep_thesis_id 外的所有 is_current 降为 false。

    F2 修复：必须赋值「新 dict 对象」——原实现原地改 JSON 再回赋同一对象，
    SQLAlchemy 变更检测视为无变化，导致 Current 切换从不落库（多 Current 腐化）。
    """
    count = 0
    rows = session.scalars(
        select(ThesisORM).where(ThesisORM.instrument_id == instrument_id)
    ).all()
    for r in rows:
        if r.thesis_id == keep_thesis_id:
            continue
        meta = r.meta_json or {}
        if meta.get("is_current"):
            r.meta_json = {**meta, "is_current": False}
            count += 1
    return count
