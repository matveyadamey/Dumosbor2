import { App, PluginSettingTab, Setting } from "obsidian";
import type TgObsidianPlugin from "./main";
import type { PluginSettings } from "./utils";

export class TgObsidianSettingTab extends PluginSettingTab {
  plugin: TgObsidianPlugin;

  constructor(app: App, plugin: TgObsidianPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "TG → Obsidian Sync" });

    const s = this.plugin.settings;

    const addText = (
      name: string,
      desc: string,
      key: keyof PluginSettings,
      placeholder = "",
    ) => {
      new Setting(containerEl)
        .setName(name)
        .setDesc(desc)
        .addText((text) =>
          text
            .setPlaceholder(placeholder)
            .setValue(String(s[key] ?? ""))
            .onChange(async (value) => {
              (this.plugin.settings[key] as string) = value.trim();
              await this.plugin.saveSettings();
            }),
        );
    };

    addText("Server URL", "Базовый URL FastAPI (без /api/v1)", "serverUrl", "http://localhost:8000");
    addText("Bearer Token", "Токен из /get_token бота", "bearerToken");
    addText("Image Path", "Папка в vault для картинок", "imagePath", "attachments");
    addText("Articles Dir", "Папка для short=false", "articlesDir", "articles");
    addText("Daily Note Dir", "Папка для short=true (YYYY-MM-DD.md)", "dailyNoteDir", "daily");
    addText(
      "YouTube File Path",
      "Путь к .md файлу с логами YouTube",
      "youtubeFilePath",
      "youtube.md",
    );

    new Setting(containerEl)
      .setName("Fetch on startup")
      .setDesc("Запускать синхронизацию при старте Obsidian")
      .addToggle((toggle) =>
        toggle.setValue(s.fetchOnStartup).onChange(async (value) => {
          this.plugin.settings.fetchOnStartup = value;
          await this.plugin.saveSettings();
        }),
      );
  }
}
