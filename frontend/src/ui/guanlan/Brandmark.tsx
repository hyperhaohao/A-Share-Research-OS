import { useTranslation } from "react-i18next";

/**
 * Guanlan Direct Port — Brandmark（donor ui/_shared/shared.jsx Brandmark → TSX）。
 * 印章 wordmark；观澜「觀瀾」字样替换为 ASRO 品牌（方案 §3 正式命名 / §27 i18n）。
 */

export interface BrandmarkProps {
  subtitle?: string;
  small?: boolean;
}

export function Brandmark({ subtitle, small }: BrandmarkProps) {
  const { t } = useTranslation();
  return (
    <div className="brandmark" style={{ display: "flex", alignItems: "center", gap: small ? 8 : 12 }}>
      <div className="seal" style={{ width: small ? 22 : 28, height: small ? 22 : 28, fontSize: small ? 14 : 16 }}>
        {t("guanlan.brandSeal")}
      </div>
      <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
        <span
          className="serif"
          style={{
            fontSize: small ? 17 : 21,
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "var(--ink)",
          }}
        >
          {t("app.title")}
        </span>
        {subtitle && (
          <span
            className="mono"
            style={{
              fontSize: 9,
              color: "var(--ink-3)",
              letterSpacing: "0.18em",
              marginTop: 4,
              textTransform: "uppercase",
            }}
          >
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
