/**
 * Telegram WebApp SDK Integration Helper.
 * Handles initialization, theme, haptic feedback, and user identity.
 */

const TelegramService = {
    tg: window.Telegram?.WebApp || null,

    init() {
        if (!this.tg) {
            console.warn("Telegram WebApp SDK not detected. Running in standard browser mode.");
            return;
        }

        try {
            this.tg.ready();
            this.tg.expand();
            
            // Set header & background colors
            if (this.tg.setHeaderColor) {
                this.tg.setHeaderColor('#FFFFFF');
            }
            if (this.tg.setBackgroundColor) {
                this.tg.setBackgroundColor('#F8FAFC');
            }
            if (this.tg.enableClosingConfirmation) {
                this.tg.enableClosingConfirmation();
            }
        } catch (e) {
            console.error("Error configuring Telegram WebApp:", e);
        }
    },

    getInitData() {
        if (this.tg && this.tg.initData) {
            return this.tg.initData;
        }
        // Fallback for direct browser testing
        return "";
    },

    getUser() {
        if (this.tg && this.tg.initDataUnsafe && this.tg.initDataUnsafe.user) {
            return this.tg.initDataUnsafe.user;
        }
        return {
            id: 999999999,
            first_name: "Гость",
            last_name: "",
            username: "guest"
        };
    },

    haptic(type = "light") {
        if (!this.tg || !this.tg.HapticFeedback) return;

        try {
            switch (type) {
                case "light":
                case "medium":
                case "heavy":
                case "rigid":
                case "soft":
                    this.tg.HapticFeedback.impactOccurred(type);
                    break;
                case "success":
                case "warning":
                case "error":
                    this.tg.HapticFeedback.notificationOccurred(type);
                    break;
                case "selection":
                    this.tg.HapticFeedback.selectionChanged();
                    break;
                default:
                    this.tg.HapticFeedback.impactOccurred("light");
            }
        } catch (e) {
            console.debug("Haptic error:", e);
        }
    },

    showBackButton(callback) {
        if (!this.tg || !this.tg.BackButton) return;
        this.tg.BackButton.show();
        this.tg.BackButton.onClick(callback);
    },

    hideBackButton() {
        if (!this.tg || !this.tg.BackButton) return;
        this.tg.BackButton.hide();
    }
};

window.TelegramService = TelegramService;
