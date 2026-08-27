import { describe, expect, it } from "vitest";
import { resolveLanguage, systemLanguage } from "../src/i18n";
import { resolveTheme } from "../src/theme/theme";

describe("language: system resolution (task书 §8)", () => {
  it("maps zh* to zh-CN", () => {
    expect(systemLanguage("zh-CN")).toBe("zh-CN");
    expect(systemLanguage("zh-TW")).toBe("zh-CN");
    expect(systemLanguage("zh")).toBe("zh-CN");
  });

  it("maps others to en-US", () => {
    expect(systemLanguage("en-US")).toBe("en-US");
    expect(systemLanguage("ja-JP")).toBe("en-US");
    expect(systemLanguage("")).toBe("en-US");
  });

  it("manual preference overrides system", () => {
    expect(resolveLanguage("en-US", "zh-CN")).toBe("en-US");
    expect(resolveLanguage("zh-CN", "en-US")).toBe("zh-CN");
    expect(resolveLanguage("system", "zh-CN")).toBe("zh-CN");
    expect(resolveLanguage("system", "en-US")).toBe("en-US");
  });
});

describe("theme: three-state resolution (task书 §12-13)", () => {
  it("system follows OS", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("manual light/dark override OS", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});
