"""Report rendering catalogs: server-side section templates (zh-CN / en-US).

Rendering reads one shared structured Research State; the two catalogs only
localize section scaffolding (labels, connective prose). Numbers, claim
statements and evidence excerpts are data — identical across languages, with
original-language text never replaced by translation (任务书 §10/§11).
"""

from __future__ import annotations

SECTIONS: dict[str, dict[str, str]] = {
    "zh-CN": {
        "report.title": "研究报告",
        "report.as_of": "数据截止",
        "report.generated_at": "生成时间",
        "section.executive_summary": "摘要",
        "section.market_and_capital": "行情与资金",
        "section.key_theses": "核心论点",
        "section.corporate_events": "公司事件",
        "section.valuation": "估值",
        "section.scenarios": "情景假设",
        "section.bull_bear": "多空辩论",
        "section.risks": "风险提示",
        "section.data_quality": "数据质量",
        "section.source_manifest": "来源清单",
        "section.disclaimer": "免责声明",
        "label.no_data": "暂无数据",
        "label.claims": "支撑主张",
        "label.evidence": "证据编号",
        "label.probability": "概率",
        "label.assumptions": "假设",
        "label.catalysts": "催化剂",
        "label.risks": "风险",
        "label.triggers": "触发条件",
        "label.invalidate": "失效条件",
        "label.implied_price": "隐含价格",
        "label.upside": "空间",
        "label.original_zh": "原文（中文）",
        "label.gate_status": "发布门",
        "disclaimer.text": (
            "本报告由系统基于公开数据自动生成，仅供研究参考，不构成投资建议。"
            "所有结论均可通过引用编号追溯至原始证据。"
        ),
    },
    "en-US": {
        "report.title": "Research Report",
        "report.as_of": "Data as of",
        "report.generated_at": "Generated at",
        "section.executive_summary": "Executive Summary",
        "section.market_and_capital": "Market & Capital",
        "section.key_theses": "Key Theses",
        "section.corporate_events": "Corporate Events",
        "section.valuation": "Valuation",
        "section.scenarios": "Scenarios",
        "section.bull_bear": "Bull / Bear",
        "section.risks": "Risks",
        "section.data_quality": "Data Quality",
        "section.source_manifest": "Source Manifest",
        "section.disclaimer": "Disclaimer",
        "label.no_data": "No data available",
        "label.claims": "Supporting claims",
        "label.evidence": "Evidence ids",
        "label.probability": "Probability",
        "label.assumptions": "Assumptions",
        "label.catalysts": "Catalysts",
        "label.risks": "Risks",
        "label.triggers": "Trigger conditions",
        "label.invalidate": "Invalidate conditions",
        "label.implied_price": "Implied price",
        "label.upside": "Upside",
        "label.original_zh": "Original (Chinese)",
        "label.gate_status": "Publication gate",
        "disclaimer.text": (
            "This report is auto-generated from public data for research "
            "reference only and is not investment advice. Every conclusion is "
            "traceable to original evidence via citation ids."
        ),
    },
}


def tr(language: str, key: str) -> str:
    catalog = SECTIONS.get(language) or SECTIONS["en-US"]
    return catalog.get(key, key)
