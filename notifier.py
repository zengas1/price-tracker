"""Telegram üzerinden bildirim göndermek için basit yardımcı fonksiyon."""

import requests


def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    """Verilen Telegram botu ve sohbet ID'si ile mesaj gönderir.

    Başarılı olursa True, olmazsa False döner (hata konsola yazılır).
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        print(f"[notifier] Telegram mesajı gönderilemedi: {exc}")
        return False
