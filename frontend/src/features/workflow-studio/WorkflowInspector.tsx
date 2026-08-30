import { useTranslation } from "react-i18next";
import { Panel, Button } from "../../ui/guanlan";
import { NODE_SPECS, type DefNode } from "./spec";

/**
 * Inspector（donor Inspector → 参数按类型编辑，方案 §15）：
 * 选中节点的标题 + 参数（text/number）+ 删除。参数 schema 来自 NODE_SPECS。
 */
export function WorkflowInspector({
  node,
  onChange,
  onDelete,
}: {
  node: DefNode | null;
  onChange: (next: DefNode) => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  if (!node) {
    return (
      <Panel title={t("studio.inspectorTitle")}>
        <p className="secondary">{t("studio.inspectorEmpty")}</p>
      </Panel>
    );
  }
  const spec = NODE_SPECS[node.kind];
  return (
    <Panel
      title={`${t(spec.titleKey)} · ${node.key}`}
      actions={
        <Button variant="ghost" onClick={onDelete}>
          {t("studio.deleteNode")}
        </Button>
      }
    >
      <div className="ws-inspector" data-testid="studio-inspector">
        <label className="ws-field">
          <span className="ws-field-label">{t("studio.param.title")}</span>
          <input
            className="control-input"
            value={node.title ?? ""}
            placeholder={t(spec.titleKey)}
            onChange={(e) => onChange({ ...node, title: e.target.value || null })}
          />
        </label>
        {spec.params.map((p) => (
          <label key={p.id} className="ws-field">
            <span className="ws-field-label">{t(p.labelKey)}</span>
            <input
              className="control-input"
              type={p.type === "number" ? "number" : "text"}
              data-testid={`studio-param-${p.id}`}
              value={String(node.params[p.id] ?? "")}
              min={p.min}
              max={p.max}
              placeholder={p.optional ? t("studio.optional") : ""}
              onChange={(e) =>
                onChange({
                  ...node,
                  params: {
                    ...node.params,
                    [p.id]:
                      p.type === "number"
                        ? Number(e.target.value)
                        : e.target.value,
                  },
                })
              }
            />
            {p.hintKey && <span className="secondary ws-field-hint">{t(p.hintKey)}</span>}
          </label>
        ))}
        {spec.params.length === 0 && (
          <p className="secondary">{t("studio.noParams")}</p>
        )}
        <p className="secondary ws-field-hint">{t(spec.descKey)}</p>
      </div>
    </Panel>
  );
}
