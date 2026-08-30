import { useTranslation } from "react-i18next";
import { NODE_CATALOG, NODE_SPECS } from "./spec";

/**
 * Node Library（donor CATALOG 分组目录 → ASRO 可执行目录，方案 §15）。
 * 点击节点类型 → 画布追加节点。
 */
export function WorkflowNodeLibrary({ onAdd }: { onAdd: (kind: string) => void }) {
  const { t } = useTranslation();
  return (
    <div className="ws-library" data-testid="studio-library">
      {NODE_CATALOG.map((group) => (
        <section key={group.groupKey} className="ws-library-group">
          <h4 className="ws-library-group-title">{t(group.groupKey)}</h4>
          {group.kinds.map((kind) => {
            const spec = NODE_SPECS[kind];
            return (
              <button
                key={kind}
                type="button"
                className="ws-library-item"
                data-testid={`studio-add-${kind}`}
                title={t(spec.descKey)}
                onClick={() => onAdd(kind)}
              >
                <span className="ws-library-dot" style={{ background: spec.color }} />
                <span className="ws-library-name">{t(spec.titleKey)}</span>
              </button>
            );
          })}
        </section>
      ))}
      <p className="secondary ws-library-hint">{t("studio.libraryHint")}</p>
    </div>
  );
}
