import { App, normalizePath, Notice, TFile } from "obsidian";
import {
  ackTexts,
  ackYoutube,
  downloadMedia,
  fetchTexts,
  fetchYoutube,
  type TextItem,
  type YoutubeItem,
} from "./api";
import {
  formatDateOnly,
  formatDuration,
  normalizeServerUrl,
  sanitizeFileName,
  stripWikiImageLinks,
  type PluginSettings,
} from "./utils";

const TELEGRAM_INBOX_HEADING = "#telegram inbox";
const DAILY_TEMPLATE_PATH = "templates/daily_note_template.md";

function joinPath(...parts: string[]): string {
  return normalizePath(parts.filter(Boolean).join("/"));
}

function todayDailyName(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}.md`;
}

async function ensureFolder(app: App, folderPath: string): Promise<void> {
  const path = normalizePath(folderPath);
  if (!path || path === ".") return;
  const parts = path.split("/");
  let current = "";
  for (const part of parts) {
    current = current ? `${current}/${part}` : part;
    if (!(await app.vault.adapter.exists(current))) {
      await app.vault.createFolder(current);
    }
  }
}

async function downloadImages(
  app: App,
  settings: PluginSettings,
  item: TextItem,
): Promise<void> {
  if (!item.images?.length) return;
  await ensureFolder(app, settings.imagePath);
  for (const fileName of item.images) {
    const dest = joinPath(settings.imagePath, fileName);
    try {
      if (await app.vault.adapter.exists(dest)) {
        continue;
      }
      const data = await downloadMedia(settings, fileName);
      await app.vault.adapter.writeBinary(dest, data);
    } catch (err) {
      console.error(`[tg-obsidian-sync] failed to save image ${fileName}`, err);
      throw err;
    }
  }
}

async function writeArticle(
  app: App,
  settings: PluginSettings,
  item: TextItem,
): Promise<void> {
  await ensureFolder(app, settings.articlesDir);
  const plain = stripWikiImageLinks(item.content);
  // только basename — на случай если санитайзер когда-то пропустит разделитель
  const base = sanitizeFileName(plain, item.message_id).replace(/[\\/]/g, "");
  let filePath = joinPath(settings.articlesDir, `${base}.md`);
  let n = 1;
  while (await app.vault.adapter.exists(filePath)) {
    filePath = joinPath(settings.articlesDir, `${base}_${n}.md`);
    n += 1;
  }
  await app.vault.create(filePath, item.content.endsWith("\n") ? item.content : `${item.content}\n`);
}

async function appendToDaily(
  app: App,
  settings: PluginSettings,
  item: TextItem,
): Promise<void> {
  await ensureFolder(app, settings.dailyNoteDir);
  const dailyPath = joinPath(settings.dailyNoteDir, todayDailyName());

  if (!(await app.vault.adapter.exists(dailyPath))) {
    let template = `# ${todayDailyName().replace(/\.md$/, "")}\n\n${TELEGRAM_INBOX_HEADING}\n`;
    try {
      if (await app.vault.adapter.exists(DAILY_TEMPLATE_PATH)) {
        template = await app.vault.adapter.read(DAILY_TEMPLATE_PATH);
        if (!template.includes(TELEGRAM_INBOX_HEADING)) {
          template = `${template.trimEnd()}\n\n${TELEGRAM_INBOX_HEADING}\n`;
        }
      }
    } catch (err) {
      console.error("[tg-obsidian-sync] failed to read daily template", err);
    }
    await app.vault.create(dailyPath, template);
  }

  const file = app.vault.getAbstractFileByPath(dailyPath);
  if (!(file instanceof TFile)) {
    throw new Error(`Daily note is not a file: ${dailyPath}`);
  }

  let body = await app.vault.read(file);
  if (!body.includes(TELEGRAM_INBOX_HEADING)) {
    body = `${body.trimEnd()}\n\n${TELEGRAM_INBOX_HEADING}\n`;
  }
  body = `${body.trimEnd()}\n${item.content.trim()}\n`;
  await app.vault.modify(file, body);
}

async function appendYoutube(
  app: App,
  settings: PluginSettings,
  item: YoutubeItem,
): Promise<void> {
  const path = normalizePath(settings.youtubeFilePath);
  const parent = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
  if (parent) {
    await ensureFolder(app, parent);
  }

  const line = `[${item.title}](${item.url}) | ${formatDuration(item.duration)} | ${formatDateOnly(item.created_at)}\n`;

  if (!(await app.vault.adapter.exists(path))) {
    await app.vault.create(path, line);
    return;
  }

  const file = app.vault.getAbstractFileByPath(path);
  if (!(file instanceof TFile)) {
    throw new Error(`YouTube file is not a file: ${path}`);
  }
  const current = await app.vault.read(file);
  const sep = current.endsWith("\n") || current.length === 0 ? "" : "\n";
  await app.vault.modify(file, `${current}${sep}${line}`);
}

export async function runSync(app: App, settings: PluginSettings): Promise<void> {
  if (!settings.serverUrl?.trim() || !settings.bearerToken?.trim()) {
    new Notice("Укажи Server URL и Bearer Token в настройках плагина");
    return;
  }

  try {
    normalizeServerUrl(settings.serverUrl);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    new Notice(msg);
    return;
  }

  new Notice("Синхронизация с сервером…");

  const texts = await fetchTexts(settings);
  const youtube = await fetchYoutube(settings);

  const ackedMessageIds: number[] = [];
  const ackedYoutubeIds: string[] = [];
  let textOk = 0;
  let textFail = 0;
  let ytOk = 0;
  let ytFail = 0;

  for (const item of texts) {
    try {
      await downloadImages(app, settings, item);
      if (item.short) {
        await appendToDaily(app, settings, item);
      } else {
        await writeArticle(app, settings, item);
      }
      ackedMessageIds.push(item.message_id);
      textOk += 1;
    } catch (err) {
      textFail += 1;
      console.error(`[tg-obsidian-sync] failed text message_id=${item.message_id}`, err);
    }
  }

  for (const item of youtube) {
    try {
      await appendYoutube(app, settings, item);
      ackedYoutubeIds.push(item.id);
      ytOk += 1;
    } catch (err) {
      ytFail += 1;
      console.error(`[tg-obsidian-sync] failed youtube id=${item.id}`, err);
    }
  }

  try {
    await ackTexts(settings, ackedMessageIds);
    await ackYoutube(settings, ackedYoutubeIds);
  } catch (err) {
    console.error("[tg-obsidian-sync] ACK failed", err);
    new Notice("Данные сохранены локально, но ACK на сервер не прошёл");
    return;
  }

  new Notice(
    `Синхронизация: тексты ${textOk}/${texts.length}, YouTube ${ytOk}/${youtube.length}` +
      (textFail || ytFail ? ` (ошибок: ${textFail + ytFail})` : ""),
  );
}
