import { describe, expect, it } from "vitest";
import {
  formatDateOnly,
  formatDuration,
  normalizeServerUrl,
  sanitizeFileName,
  stripWikiImageLinks,
} from "./utils";

describe("sanitizeFileName", () => {
  it("keeps first 20 cleaned chars", () => {
    expect(sanitizeFileName("Hello World Article Title", 1)).toBe("Hello World Article");
  });

  it("strips illegal characters", () => {
    expect(sanitizeFileName('a?b<c>d:e*f|g"h', 2)).toBe("a b c d e f g h");
  });

  it("does not create nested paths from slashes", () => {
    expect(sanitizeFileName("- Sber AI/девайсы/Камера", 3)).toBe("Sber AI девайсы Каме");
    expect(sanitizeFileName("foo\\bar\\baz", 4)).toBe("foo bar baz");
    expect(sanitizeFileName("a/b", 1).includes("/")).toBe(false);
  });

  it("uses only the first line", () => {
    expect(sanitizeFileName("Заголовок\nвторая строка длинная", 5)).toBe("Заголовок");
  });

  it("falls back for empty/emoji", () => {
    expect(sanitizeFileName("", 9)).toBe("article_9");
    expect(sanitizeFileName("🔥🔥", 9)).toBe("article_9");
    expect(sanitizeFileName("///", 9)).toBe("article_9");
  });
});

describe("normalizeServerUrl", () => {
  it("keeps http(s) URLs", () => {
    expect(normalizeServerUrl("https://app.up.railway.app/")).toBe(
      "https://app.up.railway.app",
    );
    expect(normalizeServerUrl("http://localhost:8000")).toBe("http://localhost:8000");
  });

  it("adds https when scheme is missing", () => {
    expect(normalizeServerUrl("app.up.railway.app")).toBe("https://app.up.railway.app");
  });

  it("rejects empty and bad protocols", () => {
    expect(() => normalizeServerUrl("")).toThrow(/пустой/);
    expect(() => normalizeServerUrl("ftp://example.com")).toThrow(/http/);
  });
});

describe("formatDuration", () => {
  it("formats mm:ss", () => {
    expect(formatDuration(125)).toBe("2:05");
    expect(formatDuration(0)).toBe("0:00");
    expect(formatDuration(null)).toBe("?:??");
  });
});

describe("formatDateOnly", () => {
  it("takes YYYY-MM-DD", () => {
    expect(formatDateOnly("2026-08-08T12:00:00")).toBe("2026-08-08");
  });
});

describe("stripWikiImageLinks", () => {
  it("removes wiki image embeds", () => {
    const raw = "![[attachments/1_1.jpg]]\nhello";
    expect(stripWikiImageLinks(raw)).toBe("hello");
  });
});
