export interface PluginSettings {
  serverUrl: string;
  bearerToken: string;
  imagePath: string;
  articlesDir: string;
  dailyNoteDir: string;
  youtubeFilePath: string;
  fetchOnStartup: boolean;
}

export const DEFAULT_SETTINGS: PluginSettings = {
  serverUrl: "http://localhost:8000",
  bearerToken: "",
  imagePath: "attachments",
  articlesDir: "articles",
  dailyNoteDir: "daily",
  youtubeFilePath: "youtube.md",
  fetchOnStartup: false,
};

/** Убирает недопустимые символы из имени файла; fallback при пустом/эмодзи. */
export function sanitizeFileName(text: string, messageId: number): string {
  const cleaned = (text || "")
    .replace(/[?<>\\:*|"]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 20)
    .trim();

  // если после очистки нет «обычных» символов (эмодзи/пусто) — fallback
  if (!cleaned || !/[0-9A-Za-zА-Яа-яЁё]/.test(cleaned)) {
    return `article_${messageId}`;
  }
  return cleaned;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) {
    return "?:??";
  }
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatDateOnly(iso: string): string {
  try {
    return iso.slice(0, 10);
  } catch {
    return iso;
  }
}

/** Текст без вики-ссылок на картинки — для имени статьи. */
export function stripWikiImageLinks(content: string): string {
  return (content || "")
    .replace(/!\[\[[^\]]*\]\]\n?/g, "")
    .trim();
}
