import { App, Modal, Setting } from "obsidian";

export class ConfirmCleanupModal extends Modal {
  private onConfirm: () => void;

  constructor(app: App, onConfirm: () => void) {
    super(app);
    this.onConfirm = onConfirm;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.createEl("h2", { text: "Очистить сервер?" });
    contentEl.createEl("p", {
      text: "Будут удалены записи в БД, медиа на сервере и (по возможности) сообщения в Telegram. Это действие нельзя отменить.",
    });

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Отмена").onClick(() => this.close()),
      )
      .addButton((btn) =>
        btn
          .setButtonText("Очистить")
          .setWarning()
          .onClick(() => {
            this.close();
            this.onConfirm();
          }),
      );
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
