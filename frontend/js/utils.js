/**
 * General Utilities: Formatting, Clipboard, and Toast notifications.
 */

const Utils = {
    formatPrice(amount) {
        if (typeof amount !== 'number') {
            amount = parseFloat(amount) || 0;
        }
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            maximumFractionDigits: 0
        }).format(amount);
    },

    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('ru-RU', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    },

    async copyToClipboard(text, label = "Реквизиты скопированы") {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
            } else {
                // Fallback for non-https or older webviews
                const textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.opacity = "0";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }

            TelegramService.haptic("success");
            this.showToast(`✓ ${label}`, "success");
            return true;
        } catch (err) {
            console.error('Failed to copy: ', err);
            this.showToast("Не удалось скопировать", "error");
            return false;
        }
    },

    showToast(message, type = "info") {
        const existingToast = document.getElementById("global-toast");
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement("div");
        toast.id = "global-toast";
        
        let bgClass = "bg-slate-900 text-white";
        if (type === "success") {
            bgClass = "bg-emerald-600 text-white";
        } else if (type === "error") {
            bgClass = "bg-rose-600 text-white";
        }

        toast.className = `fixed top-5 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-full shadow-lg text-sm font-medium transition-all duration-300 transform scale-95 opacity-0 flex items-center gap-2 ${bgClass}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove("scale-95", "opacity-0");
            toast.classList.add("scale-100", "opacity-100");
        });

        // Auto dismiss
        setTimeout(() => {
            toast.classList.remove("scale-100", "opacity-100");
            toast.classList.add("scale-95", "opacity-0");
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }
};

window.Utils = Utils;
