"""
Cloudflare Tunnel Launcher for TMA Shop.
Provides clean, direct HTTPS tunnel without warning interstitial pages.
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CLOUDFLARED_PATH = BASE_DIR / "cloudflared.exe"

def main():
    print("================================================================")
    print("🚀 Запуск Cloudflare HTTPS туннеля для Telegram Mini App...")
    print("================================================================")
    print("Туннель Cloudflare не требует регистрации и НЕ показывает")
    print("предупреждающих экранов — магазин откроется сразу.")
    print("Ищите в выводе ниже ссылку вида: https://xxxx.trycloudflare.com\n")

    if not CLOUDFLARED_PATH.exists():
        print(f"Ошибка: {CLOUDFLARED_PATH} не найден.")
        return

    cmd = [str(CLOUDFLARED_PATH), "tunnel", "--url", "http://localhost:8000"]

    try:
        # Run directly attached to console so cloudflare prints the URL cleanly
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nТуннель остановлен.")

if __name__ == "__main__":
    main()
