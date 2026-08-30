"""Research Memory（R7，方案 §13）：版本化研究记忆 —— 方法，不是事实.

Memory 类型（§13.1）：company / industry / event_playbook / research_method /
known_failure / research_checklist / user_preference。
边界（§13.4）：Memory 只用于提问/选方法/找风险/找反例/复用框架 ——
结构上不携带 authority/fact_status（那些是 Evidence 字段），Agent Prompt
三段上下文（Evidence/Memory/User）由检索接口分别返回锁定。

晋升（§13.5）：candidate（staging）→ review → active/retired；
不自动把聊天写为正式记忆（donor _pending_introspections 语义）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


VALID_MEMORY_TYPES = (
    "company",
    "industry",
    "event_playbook",
    "research_method",
    "known_failure",
    "research_checklist",
    "user_preference",
)
VALID_MEMORY_STATUS = ("candidate", "active", "retired")


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class ResearchMemoryORM(Base):
    __tablename__ = "research_memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    memory_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(4000))
    instrument_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    industry_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(24), nullable=True)
    tags_json: Mapped[list] = mapped_column(JSON, default=list)
    source_artifacts_json: Mapped[list] = mapped_column(JSON, default=list)
    source_experiences_json: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="candidate", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _to_dict(row: ResearchMemoryORM) -> dict:
    return {
        "memory_id": row.memory_id,
        "memory_type": row.memory_type,
        "title": row.title,
        "content": row.content,
        "scope": {
            "instrument_id": row.instrument_id,
            "industry_id": row.industry_id,
            "event_type": row.event_type,
            "intent": row.intent,
            "tags": list(row.tags_json or []),
        },
        "source_artifacts": list(row.source_artifacts_json or []),
        "source_experiences": list(row.source_experiences_json or []),
        "status": row.status,
        "version": row.version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: ResearchMemoryORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _to_dict(row)

    def get(self, memory_id: str) -> dict | None:
        row = self._session.scalars(
            select(ResearchMemoryORM).where(ResearchMemoryORM.memory_id == memory_id)
        ).first()
        return None if row is None else _to_dict(row)

    def search(
        self,
        *,
        memory_type: str | None = None,
        status: str | None = "active",
        instrument_id: str | None = None,
        industry_id: str | None = None,
        event_type: str | None = None,
        intent: str | None = None,
        q: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        stmt = select(ResearchMemoryORM).order_by(
            ResearchMemoryORM.updated_at.desc(), ResearchMemoryORM.id.desc()
        )
        if memory_type:
            stmt = stmt.where(ResearchMemoryORM.memory_type == memory_type)
        if status:
            stmt = stmt.where(ResearchMemoryORM.status == status)
        if instrument_id:
            stmt = stmt.where(ResearchMemoryORM.instrument_id == instrument_id)
        if industry_id:
            stmt = stmt.where(ResearchMemoryORM.industry_id == industry_id)
        if event_type:
            stmt = stmt.where(ResearchMemoryORM.event_type == event_type)
        if intent:
            stmt = stmt.where(ResearchMemoryORM.intent == intent)
        rows = self._session.scalars(stmt).all()
        out = []
        qn = (q or "").strip()
        for r in rows:
            d = _to_dict(r)
            if qn:
                hay = " ".join([d["title"], d["content"], " ".join(d["scope"]["tags"])])
                if qn not in hay:
                    continue
            out.append(d)
            if len(out) >= limit:
                break
        return out


class MemoryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = MemoryRepository(session)

    def create_candidate(
        self,
        *,
        memory_type: str,
        title: str,
        content: str,
        scope: dict | None = None,
        source_artifacts: list[str] | None = None,
        source_experiences: list[str] | None = None,
    ) -> dict:
        """新记忆一律 candidate（方案 §13.5：不自动写正式记忆）。"""
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(f"unknown memory type: {memory_type}")
        now = _utc()
        scope = scope or {}
        row = ResearchMemoryORM(
            memory_id="mem_" + uuid4().hex[:12],
            memory_type=memory_type,
            title=title[:200],
            content=content[:4000],
            instrument_id=scope.get("instrument_id"),
            industry_id=scope.get("industry_id"),
            event_type=scope.get("event_type"),
            intent=scope.get("intent"),
            tags_json=list(scope.get("tags") or []),
            source_artifacts_json=list(source_artifacts or []),
            source_experiences_json=list(source_experiences or []),
            status="candidate",
            version=1,
            created_at=now,
            updated_at=now,
        )
        return self._repo.add(row)

    def promote(self, memory_id: str) -> dict:
        """candidate → active；active → retired（人工晋升门，禁跳级）。"""
        row = self._session.scalars(
            select(ResearchMemoryORM).where(ResearchMemoryORM.memory_id == memory_id)
        ).first()
        if row is None:
            raise KeyError(memory_id)
        if row.status == "candidate":
            row.status = "active"
        elif row.status == "active":
            row.status = "retired"
        row.version += 1
        row.updated_at = _utc()
        self._session.flush()
        return _to_dict(row)

    def update_content(self, memory_id: str, *, content: str) -> dict:
        """内容更新 = version+1（版本可追溯；更细的多行版本表在 R9 需要时再拆）。"""
        row = self._session.scalars(
            select(ResearchMemoryORM).where(ResearchMemoryORM.memory_id == memory_id)
        ).first()
        if row is None:
            raise KeyError(memory_id)
        row.content = content[:4000]
        row.version += 1
        row.updated_at = _utc()
        self._session.flush()
        return _to_dict(row)

    def search(self, **kw: Any) -> list[dict]:
        return self._repo.search(**kw)

    def from_experience(self, card_id: str, *, memory_type: str = "research_method") -> dict:
        """Experience → candidate Memory（方案 §13.5，源引用保留）。"""
        from app.application.artifacts import ArtifactService
        from app.application.experience import ExperienceRepository

        row = ExperienceRepository(self._session).get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        if row.status != "APPROVED":
            raise ValueError("only APPROVED experiences can become memory candidates")
        artifact = ArtifactService(self._session).by_domain("ExperienceCard", card_id)
        scope: dict = {
            "tags": list(row.applicable_conditions_json or [])[:3],
            "instrument_id": row.instrument_id,
        }
        return self.create_candidate(
            memory_type=memory_type,
            title=f"{row.title}（经验方法）",
            content=row.mechanism or row.statement,
            scope=scope,
            source_experiences=[card_id],
            source_artifacts=[artifact["artifact_id"]] if artifact else [],
        )
