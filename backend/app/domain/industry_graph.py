"""Industry Graph 域模型（G1，观澜语义迁移任务书 §G1）.

产业链 ≠ 行业分类：本模块建立可计算、可引用、可 PIT 的产业图谱。

    IndustryChain（链）
      └─ IndustrySegment（环节，stage_order）
           ├─ IndustryEdge（传导边：9 类 relation/方向/时滞/强度/置信）
           │    └─ IndustryEdgeEvidence（支撑/反对证据，append-only 链接）
           ├─ IndustryProduct（环节投入/产出物）
           └─ CompanyIndustryPosition（公司在链上的角色与暴露）

PIT 语义：
  - Edge/Position 携 valid_from/valid_to + created_at；as_of 过滤可重放；
  - Edge 的证据可用时间必须 ≤ as_of（Evidence Ownership Gate，G2 复用）；
  - 图版本（version）随结构变更单调递增，历史可重放。

置信语义（任务书 §G1 DoD）：
  - 删除关键 Edge Evidence 后边自动降级（active → degraded）；
  - 无支撑证据的边不可发布（置信 insufficient）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class RelationType(str, Enum):
    """传导关系九类（任务书 §G1）。"""

    MATERIAL_FLOW = "material_flow"
    PRICE_TRANSMISSION = "price_transmission"
    COST_TRANSMISSION = "cost_transmission"
    PROFIT_TRANSMISSION = "profit_transmission"
    DEMAND_TRANSMISSION = "demand_transmission"
    SUPPLY_CONSTRAINT = "supply_constraint"
    POLICY_TRANSMISSION = "policy_transmission"
    SUBSTITUTION = "substitution"
    COMPETITION = "competition"


class CompanyRole(str, Enum):
    PRODUCER = "producer"
    PROCESSOR = "processor"
    CONSUMER = "consumer"
    SUPPLIER = "supplier"
    RECYCLER = "recycler"


# 边状态：无支撑证据 → insufficient（不可发布）；关键证据缺失 → degraded
EDGE_STATUSES = ("active", "degraded", "insufficient", "retired")

# 发布门槛：至少 N 条支撑证据
MIN_PUBLISH_EVIDENCE = 1


@dataclass
class IndustryChain:
    chain_id: str = field(default_factory=lambda: f"chain_{uuid4().hex[:16]}")
    name: str = ""
    description: str = ""
    version: int = 1
    created_at: datetime | None = None


@dataclass
class IndustrySegment:
    segment_id: str = field(default_factory=lambda: f"seg_{uuid4().hex[:16]}")
    chain_id: str = ""
    name: str = ""
    stage_order: int = 0
    description: str = ""
    created_at: datetime | None = None


@dataclass
class IndustryProduct:
    product_id: str = field(default_factory=lambda: f"prd_{uuid4().hex[:16]}")
    name: str = ""
    unit: str = ""
    description: str = ""
    created_at: datetime | None = None


@dataclass
class IndustryEdge:
    edge_id: str = field(default_factory=lambda: f"edge_{uuid4().hex[:16]}")
    chain_id: str = ""
    source_segment_id: str = ""
    target_segment_id: str = ""
    relation_type: str = RelationType.MATERIAL_FLOW.value
    input_product_ids: tuple[str, ...] = ()
    output_product_ids: tuple[str, ...] = ()
    transmission_metric: str = ""      # 传导度量（如 氧化镨钕价格、配额量）
    direction: str = "positive"        # positive | negative
    lag_min_days: int = 0
    lag_max_days: int = 0
    strength: float = 0.0              # 0-1（由证据支撑度派生，非拍脑袋）
    confidence_level: str = "insufficient"  # high|medium|low|insufficient
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    status: str = "insufficient"
    version: int = 1
    snapshot_id: str | None = None
    created_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass
class IndustryEdgeEvidenceLink:
    link_id: str = field(default_factory=lambda: f"eev_{uuid4().hex[:16]}")
    edge_id: str = ""
    evidence_id: str = ""
    stance: str = "support"            # support | contrary
    added_at: datetime | None = None
    added_by: str = "industry_graph"


@dataclass
class CompanyIndustryPosition:
    position_id: str = field(default_factory=lambda: f"pos_{uuid4().hex[:16]}")
    instrument_id: str = ""
    chain_id: str = ""
    segment_id: str = ""
    role: str = CompanyRole.PRODUCER.value
    revenue_exposure_pct: float | None = None
    profit_exposure_pct: float | None = None
    capacity_note: str = ""            # 产能/业务依据（文字，引用证据）
    evidence_ids: tuple[str, ...] = ()
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    snapshot_id: str | None = None
    version: int = 1
    created_at: datetime | None = None
