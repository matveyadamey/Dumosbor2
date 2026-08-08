import { Notice, Plugin } from "obsidian";
import { cleanupServer } from "./api";
import { ConfirmCleanupModal } from "./cleanupModal";
import { TgObsidianSettingTab } from "./settings";
import { runSync } from "./sync";
import { DEFAULT_SETTINGS, type PluginSettings } from "./utils";

export default class TgObsidianPlugin extends Plugin {
  settings: PluginSettings = { ...DEFAULT_SETTINGS };

  async onload(): Promise<void> {
    await this.loadSettings();
    this.addSettingTab(new TgObsidianSettingTab(this.app, this));

    this.addCommand({
      id: "tg-obsidian-sync",
      name: "Синхронизировать",
      callback: async () => {
        try {
          await runSync(this.app, this.settings);
        } catch (err) {
          console.error("[tg-obsidian-sync] sync failed", err);
          new Notice("Ошибка синхронизации — смотри консоль");
        }
      },
    });

    this.addCommand({
      id: "tg-obsidian-cleanup",
      name: "Очистить сервер",
      callback: () => {
        new ConfirmCleanupModal(this.app, async () => {
          try {
            await cleanupServer(this.settings);
            new Notice("Сервер очищен");
          } catch (err) {
            console.error("[tg-obsidian-sync] cleanup failed", err);
            new Notice("Не удалось очистить сервер");
          }
        }).open();
      },
    });

    this.addRibbonIcon("sync", "Синхронизировать Telegram", async () => {
      try {
        await runSync(this.app, this.settings);
      } catch (err) {
        console.error("[tg-obsidian-sync] sync failed", err);
        new Notice("Ошибка синхронизации — смотри консоль");
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

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}
