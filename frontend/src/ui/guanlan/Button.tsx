import type { ButtonHTMLAttributes } from "react";

/**
 * Guanlan port — Button（G0 基础组件集，方案 §31）。
 * 细墨边按钮；primary = 墨底纸字；ghost = 无边框。原生 button 语义保持。
 */

export type ButtonVariant = "default" | "primary" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({ variant = "default", className, type, ...rest }: ButtonProps) {
  const variantCls = variant === "default" ? "" : ` gl-button-${variant}`;
  return (
    <button
      type={type ?? "button"}
      className={`gl-button${variantCls}${className ? ` ${className}` : ""}`}
      {...rest}
    />
  );
}
