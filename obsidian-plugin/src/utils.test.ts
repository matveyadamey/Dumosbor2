import { describe, expect, it } from "vitest";
import {
  formatDateOnly,
  formatDuration,
  sanitizeFileName,
  stripWikiImageLinks,
} from "./utils";

describe("sanitizeFileName", () => {
  it("keeps first 20 cleaned chars", () => {
    expect(sanitizeFileName("Hello World Article Title", 1)).toBe("Hello World Article");
  });

  it("strips illegal characters", () => {
    expect(sanitizeFileName('a?b<c>d:e*f|g"h', 2)).toBe("abcdefgh");
  });

  it("falls back for empty/emoji", () => {
    expect(sanitizeFileName("", 9)).toBe("article_9");
    expect(sanitizeFileName("🔥🔥", 9)).toBe("article_9");
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
