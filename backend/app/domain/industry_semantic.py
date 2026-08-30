"""产业研究语义 Domain（R3，方案 §9）.

四个一等研究对象：IndustryDriver / IndustryTransmission / IndustryNarrative /
SegmentPosition。全部 append-only 版本化（更新=新版本行），全部必须挂
evidence_refs（创建/更新时经 CitationVerifier 反查，无引用不进正式研究状态）。
"""

from __future__ import annotations

from enum import Enum


class DriverDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class NarrativeStatus(str, Enum):
    EMERGING = "emerging"
    ACTIVE = "active"
    WEAKENING = "weakening"
    INVALIDATED = "invalidated"
    UNCERTAIN = "uncertain"


class TransmissionDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNCERTAIN = "uncertain"


class PositionAxis(str, Enum):
    GLOBAL_DEMAND = "global_demand"            # β
    PRICING_CYCLE = "pricing_cycle"            # Δ
    DOMESTIC_SUBSTITUTION = "domestic_substitution"  # Ω
    TECHNOLOGY_ROUTE = "technology_route"      # Θ
    THEME_MAPPING = "theme_mapping"            # Ψ


class NarrativeTemperature(str, Enum):
    """「温度」= 研究注意力/证据强度（可复算：近窗证据计数对比），不是买卖评分。

    数据不足时显形 insufficient（方案 §9.5：没有可靠可复算定义就不展示数字）。
    """

    WARMING = "warming"
    STABLE = "stable"
    COOLING = "cooling"
    INSUFFICIENT = "insufficient"


VALID_DIRECTIONS = tuple(d.value for d in DriverDirection)
VALID_NARRATIVE_STATUSES = tuple(s.value for s in NarrativeStatus)
VALID_TRANSMISSION_DIRECTIONS = tuple(d.value for d in TransmissionDirection)
VALID_AXES = tuple(a.value for a in PositionAxis)
