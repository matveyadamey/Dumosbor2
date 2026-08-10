var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => TgObsidianPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian5 = require("obsidian");

// src/api.ts
var import_obsidian = require("obsidian");

// src/utils.ts
var DEFAULT_SETTINGS = {
  serverUrl: "http://localhost:8000",
  bearerToken: "",
  imagePath: "attachments",
  articlesDir: "articles",
  dailyNoteDir: "daily",
  youtubeFilePath: "youtube.md",
  fetchOnStartup: false
};
function normalizeServerUrl(raw) {
  let url = (raw || "").trim().replace(/\/+$/, "");
  if (!url) {
    throw new Error("Server URL \u043F\u0443\u0441\u0442\u043E\u0439 \u2014 \u0443\u043A\u0430\u0436\u0438 \u0430\u0434\u0440\u0435\u0441 API \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430\u0445 \u043F\u043B\u0430\u0433\u0438\u043D\u0430");
  }
  if (!/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(url)) {
    url = `https://${url}`;
  }
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`\u041D\u0435\u043A\u043E\u0440\u0440\u0435\u043A\u0442\u043D\u044B\u0439 Server URL: ${raw}`);
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `Server URL \u0434\u043E\u043B\u0436\u0435\u043D \u043D\u0430\u0447\u0438\u043D\u0430\u0442\u044C\u0441\u044F \u0441 http:// \u0438\u043B\u0438 https:// (\u0441\u0435\u0439\u0447\u0430\u0441: ${parsed.protocol})`
    );
  }
  return `${parsed.origin}${parsed.pathname}`.replace(/\/+$/, "");
}
function sanitizeFileName(text, messageId) {
  const firstLine = (text || "").split(/\r?\n/, 1)[0] ?? "";
  let cleaned = firstLine.replace(/[?<>\\/:*|"\u0000-\u001f]/g, " ").replace(/[“”«»„]/g, "").replace(/\s+/g, " ").trim().replace(/^[.\s_-]+/, "").replace(/[.\s]+$/, "").slice(0, 20).replace(/[.\s]+$/, "").trim();
  cleaned = cleaned.replace(/[\\/]/g, "").trim();
  if (!cleaned || !/[0-9A-Za-zА-Яа-яЁё]/.test(cleaned)) {
    return `article_${messageId}`;
  }
  return cleaned;
}
function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) {
    return "?:??";
  }
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
function formatDateOnly(iso) {
  try {
    return iso.slice(0, 10);
  } catch {
    return iso;
  }
}
function stripWikiImageLinks(content) {
  return (content || "").replace(/!\[\[[^\]]*\]\]\n?/g, "").trim();
}

// src/api.ts
function apiBase(settings) {
  return normalizeServerUrl(settings.serverUrl);
}
function authHeaders(settings) {
  return {
    Authorization: `Bearer ${settings.bearerToken}`
  };
}
async function apiJson(settings, method, path, body) {
  const url = `${apiBase(settings)}${path}`;
  try {
    const res = await (0, import_obsidian.requestUrl)({
      url,
      method,
      headers: {
        ...authHeaders(settings),
        ...body !== void 0 ? { "Content-Type": "application/json" } : {}
      },
      body: body !== void 0 ? JSON.stringify(body) : void 0,
      throw: false
    });
    if (res.status < 200 || res.status >= 300) {
      throw new Error(`HTTP ${res.status} ${method} ${path}: ${res.text}`);
    }
    if (!res.text) {
      return {};
    }
    return JSON.parse(res.text);
  } catch (err) {
    console.error(`[tg-obsidian-sync] ${method} ${path} failed`, err);
    throw err;
  }
}
async function fetchTexts(settings) {
  return apiJson(settings, "GET", "/api/v1/texts?limit=200&offset=0");
}
async function fetchYoutube(settings) {
  return apiJson(settings, "GET", "/api/v1/youtube");
}
async function ackTexts(settings, messageIds) {
  if (!messageIds.length)
    return;
  await apiJson(settings, "POST", "/api/v1/texts/ack", { message_ids: messageIds });
}
async function ackYoutube(settings, ids) {
  if (!ids.length)
    return;
  await apiJson(settings, "POST", "/api/v1/youtube/ack", { ids });
}
async function cleanupServer(settings) {
  await apiJson(settings, "DELETE", "/api/v1/cleanup");
}
async function downloadMedia(settings, fileName) {
  const url = `${apiBase(settings)}/api/v1/media/${encodeURIComponent(fileName)}`;
  try {
    const res = await (0, import_obsidian.requestUrl)({
      url,
      method: "GET",
      headers: authHeaders(settings),
      throw: false
    });
    if (res.status < 200 || res.status >= 300) {
      throw new Error(`HTTP ${res.status} downloading ${fileName}`);
    }
    return res.arrayBuffer;
  } catch (err) {
    console.error(`[tg-obsidian-sync] media download failed: ${fileName}`, err);
    throw err;
  }
}

// src/cleanupModal.ts
var import_obsidian2 = require("obsidian");
var ConfirmCleanupModal = class extends import_obsidian2.Modal {
  constructor(app, onConfirm) {
    super(app);
    this.onConfirm = onConfirm;
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.createEl("h2", { text: "\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C \u0441\u0435\u0440\u0432\u0435\u0440?" });
    contentEl.createEl("p", {
      text: "\u0411\u0443\u0434\u0443\u0442 \u0443\u0434\u0430\u043B\u0435\u043D\u044B \u0437\u0430\u043F\u0438\u0441\u0438 \u0432 \u0411\u0414, \u043C\u0435\u0434\u0438\u0430 \u043D\u0430 \u0441\u0435\u0440\u0432\u0435\u0440\u0435 \u0438 (\u043F\u043E \u0432\u043E\u0437\u043C\u043E\u0436\u043D\u043E\u0441\u0442\u0438) \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u044F \u0432 Telegram. \u042D\u0442\u043E \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043D\u0435\u043B\u044C\u0437\u044F \u043E\u0442\u043C\u0435\u043D\u0438\u0442\u044C."
    });
    new import_obsidian2.Setting(contentEl).addButton(
      (btn) => btn.setButtonText("\u041E\u0442\u043C\u0435\u043D\u0430").onClick(() => this.close())
    ).addButton(
      (btn) => btn.setButtonText("\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C").setWarning().onClick(() => {
        this.close();
        this.onConfirm();
      })
    );
  }
  onClose() {
    this.contentEl.empty();
  }
};

// src/settings.ts
var import_obsidian3 = require("obsidian");
var TgObsidianSettingTab = class extends import_obsidian3.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "TG \u2192 Obsidian Sync" });
    const s = this.plugin.settings;
    const addText = (name, desc, key, placeholder = "") => {
      new import_obsidian3.Setting(containerEl).setName(name).setDesc(desc).addText(
        (text) => text.setPlaceholder(placeholder).setValue(String(s[key] ?? "")).onChange(async (value) => {
          this.plugin.settings[key] = value.trim();
          await this.plugin.saveSettings();
        })
      );
    };
    addText(
      "Server URL",
      "\u0411\u0430\u0437\u043E\u0432\u044B\u0439 URL FastAPI \u0441 https:// (\u0431\u0435\u0437 /api/v1). \u041F\u0440\u0438\u043C\u0435\u0440: https://xxx.up.railway.app",
      "serverUrl",
      "https://your-app.up.railway.app"
    );
    addText("Bearer Token", "\u0422\u043E\u043A\u0435\u043D \u0438\u0437 /get_token \u0431\u043E\u0442\u0430", "bearerToken");
    addText("Image Path", "\u041F\u0430\u043F\u043A\u0430 \u0432 vault \u0434\u043B\u044F \u043A\u0430\u0440\u0442\u0438\u043D\u043E\u043A", "imagePath", "attachments");
    addText("Articles Dir", "\u041F\u0430\u043F\u043A\u0430 \u0434\u043B\u044F short=false", "articlesDir", "articles");
    addText("Daily Note Dir", "\u041F\u0430\u043F\u043A\u0430 \u0434\u043B\u044F short=true (YYYY-MM-DD.md)", "dailyNoteDir", "daily");
    addText(
      "YouTube File Path",
      "\u041F\u0443\u0442\u044C \u043A .md \u0444\u0430\u0439\u043B\u0443 \u0441 \u043B\u043E\u0433\u0430\u043C\u0438 YouTube",
      "youtubeFilePath",
      "youtube.md"
    );
    new import_obsidian3.Setting(containerEl).setName("Fetch on startup").setDesc("\u0417\u0430\u043F\u0443\u0441\u043A\u0430\u0442\u044C \u0441\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0430\u0446\u0438\u044E \u043F\u0440\u0438 \u0441\u0442\u0430\u0440\u0442\u0435 Obsidian").addToggle(
      (toggle) => toggle.setValue(s.fetchOnStartup).onChange(async (value) => {
        this.plugin.settings.fetchOnStartup = value;
        await this.plugin.saveSettings();
      })
    );
  }
};

// src/sync.ts
var import_obsidian4 = require("obsidian");
var TELEGRAM_INBOX_HEADING = "#telegram inbox";
var DAILY_TEMPLATE_PATH = "templates/daily_note_template.md";
function joinPath(...parts) {
  return (0, import_obsidian4.normalizePath)(parts.filter(Boolean).join("/"));
}
function todayDailyName() {
  const d = /* @__PURE__ */ new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}.md`;
}
async function ensureFolder(app, folderPath) {
  const path = (0, import_obsidian4.normalizePath)(folderPath);
  if (!path || path === ".")
    return;
  const parts = path.split("/");
  let current = "";
  for (const part of parts) {
    current = current ? `${current}/${part}` : part;
    if (!await app.vault.adapter.exists(current)) {
      await app.vault.createFolder(current);
    }
  }
}
async function downloadImages(app, settings, item) {
  if (!item.images?.length)
    return;
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
async function writeArticle(app, settings, item) {
  await ensureFolder(app, settings.articlesDir);
  const plain = stripWikiImageLinks(item.content);
  const base = sanitizeFileName(plain, item.message_id).replace(/[\\/]/g, "");
  let filePath = joinPath(settings.articlesDir, `${base}.md`);
  let n = 1;
  while (await app.vault.adapter.exists(filePath)) {
    filePath = joinPath(settings.articlesDir, `${base}_${n}.md`);
    n += 1;
  }
  await app.vault.create(filePath, item.content.endsWith("\n") ? item.content : `${item.content}
`);
}
async function appendToDaily(app, settings, item) {
  await ensureFolder(app, settings.dailyNoteDir);
  const dailyPath = joinPath(settings.dailyNoteDir, todayDailyName());
  if (!await app.vault.adapter.exists(dailyPath)) {
    let template = `# ${todayDailyName().replace(/\.md$/, "")}

${TELEGRAM_INBOX_HEADING}
`;
    try {
      if (await app.vault.adapter.exists(DAILY_TEMPLATE_PATH)) {
        template = await app.vault.adapter.read(DAILY_TEMPLATE_PATH);
        if (!template.includes(TELEGRAM_INBOX_HEADING)) {
          template = `${template.trimEnd()}

${TELEGRAM_INBOX_HEADING}
`;
        }
      }
    } catch (err) {
      console.error("[tg-obsidian-sync] failed to read daily template", err);
    }
    await app.vault.create(dailyPath, template);
  }
  const file = app.vault.getAbstractFileByPath(dailyPath);
  if (!(file instanceof import_obsidian4.TFile)) {
    throw new Error(`Daily note is not a file: ${dailyPath}`);
  }
  let body = await app.vault.read(file);
  if (!body.includes(TELEGRAM_INBOX_HEADING)) {
    body = `${body.trimEnd()}

${TELEGRAM_INBOX_HEADING}
`;
  }
  body = `${body.trimEnd()}
${item.content.trim()}
`;
  await app.vault.modify(file, body);
}
async function appendYoutube(app, settings, item) {
  const path = (0, import_obsidian4.normalizePath)(settings.youtubeFilePath);
  const parent = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
  if (parent) {
    await ensureFolder(app, parent);
  }
  const line = `[${item.title}](${item.url}) | ${formatDuration(item.duration)} | ${formatDateOnly(item.created_at)}
`;
  if (!await app.vault.adapter.exists(path)) {
    await app.vault.create(path, line);
    return;
  }
  const file = app.vault.getAbstractFileByPath(path);
  if (!(file instanceof import_obsidian4.TFile)) {
    throw new Error(`YouTube file is not a file: ${path}`);
  }
  const current = await app.vault.read(file);
  const sep = current.endsWith("\n") || current.length === 0 ? "" : "\n";
  await app.vault.modify(file, `${current}${sep}${line}`);
}
async function runSync(app, settings) {
  if (!settings.serverUrl?.trim() || !settings.bearerToken?.trim()) {
    new import_obsidian4.Notice("\u0423\u043A\u0430\u0436\u0438 Server URL \u0438 Bearer Token \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430\u0445 \u043F\u043B\u0430\u0433\u0438\u043D\u0430");
    return;
  }
  try {
    normalizeServerUrl(settings.serverUrl);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    new import_obsidian4.Notice(msg);
    return;
  }
  new import_obsidian4.Notice("\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0430\u0446\u0438\u044F \u0441 \u0441\u0435\u0440\u0432\u0435\u0440\u043E\u043C\u2026");
  const texts = await fetchTexts(settings);
  const youtube = await fetchYoutube(settings);
  const ackedMessageIds = [];
  const ackedYoutubeIds = [];
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
    new import_obsidian4.Notice("\u0414\u0430\u043D\u043D\u044B\u0435 \u0441\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u044B \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u043E, \u043D\u043E ACK \u043D\u0430 \u0441\u0435\u0440\u0432\u0435\u0440 \u043D\u0435 \u043F\u0440\u043E\u0448\u0451\u043B");
    return;
  }
  new import_obsidian4.Notice(
    `\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0430\u0446\u0438\u044F: \u0442\u0435\u043A\u0441\u0442\u044B ${textOk}/${texts.length}, YouTube ${ytOk}/${youtube.length}` + (textFail || ytFail ? ` (\u043E\u0448\u0438\u0431\u043E\u043A: ${textFail + ytFail})` : "")
  );
}

// src/main.ts
var TgObsidianPlugin = class extends import_obsidian5.Plugin {
  constructor() {
    super(...arguments);
    this.settings = { ...DEFAULT_SETTINGS };
  }
  async onload() {
    await this.loadSettings();
    this.addSettingTab(new TgObsidianSettingTab(this.app, this));
    this.addCommand({
      id: "tg-obsidian-sync",
      name: "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u043E\u0432\u0430\u0442\u044C",
      callback: async () => {
        try {
          await runSync(this.app, this.settings);
        } catch (err) {
          console.error("[tg-obsidian-sync] sync failed", err);
          new import_obsidian5.Notice("\u041E\u0448\u0438\u0431\u043A\u0430 \u0441\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0430\u0446\u0438\u0438 \u2014 \u0441\u043C\u043E\u0442\u0440\u0438 \u043A\u043E\u043D\u0441\u043E\u043B\u044C");
        }
      }
    });
    this.addCommand({
      id: "tg-obsidian-cleanup",
      name: "\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C \u0441\u0435\u0440\u0432\u0435\u0440",
      callback: () => {
        new ConfirmCleanupModal(this.app, async () => {
          try {
            await cleanupServer(this.settings);
            new import_obsidian5.Notice("\u0421\u0435\u0440\u0432\u0435\u0440 \u043E\u0447\u0438\u0449\u0435\u043D");
          } catch (err) {
            console.error("[tg-obsidian-sync] cleanup failed", err);
            new import_obsidian5.Notice("\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u043E\u0447\u0438\u0441\u0442\u0438\u0442\u044C \u0441\u0435\u0440\u0432\u0435\u0440");
          }
        }).open();
      }
    });
    this.addRibbonIcon("sync", "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u043E\u0432\u0430\u0442\u044C Telegram", async () => {
      try {
        await runSync(this.app, this.settings);
      } catch (err) {
        console.error("[tg-obsidian-sync] sync failed", err);
        new import_obsidian5.Notice("\u041E\u0448\u0438\u0431\u043A\u0430 \u0441\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0430\u0446\u0438\u0438 \u2014 \u0441\u043C\u043E\u0442\u0440\u0438 \u043A\u043E\u043D\u0441\u043E\u043B\u044C");
      }
    });
    if (this.settings.fetchOnStartup) {
      this.app.workspace.onLayoutReady(() => {
        void runSync(this.app, this.settings).catch((err) => {
          console.error("[tg-obsidian-sync] startup sync failed", err);
        });
      });
    }
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
};
