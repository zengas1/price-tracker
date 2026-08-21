"""Telegram botuna gelen mesajları dinleyip ürün linklerini otomatik takibe ekler.

Kullanıcı bota bir ürün linki attığında: sayfayı çeker, JSON-LD'den ürün
adını okur, config.json'daki products listesine ekler ve "eklendi" diye
onay mesajı gönderir. Zaten takip edilen bir link tekrar atılırsa uyarır.
"""

import re

import requests

from notifier import send_message

URL_PATTERN = re.compile(r"https?://\S+")


def get_updates(bot_token: str, offset: int):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        response = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=15)
        response.raise_for_status()
        return response.json().get("result", [])
    except requests.RequestException as exc:
        print(f"[link_bot] Telegram güncellemeleri alınamadı: {exc}")
        return []


def process_incoming_links(config: dict, state: dict, telegram: dict, fetch_soup, extract_from_jsonld) -> bool:
    """Yeni Telegram mesajlarını kontrol eder, link varsa config'e ekler.

    Config değiştiyse True döner (çağıran taraf config.json'ı diske yazmalı).
    """
    bot_token = telegram.get("bot_token")
    if not bot_token:
        return False

    last_offset = state.get("_bot_offset", 0)
    updates = get_updates(bot_token, last_offset + 1)
    if not updates:
        return False

    products = config.setdefault("products", [])
    known_urls = {p["url"] for p in products}
    changed = False

    for update in updates:
        state["_bot_offset"] = update["update_id"]

        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        match = URL_PATTERN.search(text)
        if not match or chat_id is None:
            continue

        url = match.group(0)
        if url in known_urls:
            send_message(bot_token, chat_id, "Bu ürün zaten takip listende.")
            continue

        soup, error = fetch_soup(url)
        if soup is None:
            send_message(bot_token, chat_id, f"Sayfa alınamadı, ekleyemedim: {error}")
            continue

        name, price, in_stock = extract_from_jsonld(soup)
        if not name:
            title_tag = soup.find("title")
            name = title_tag.get_text().strip() if title_tag else url

        products.append({"name": name, "url": url, "price_selector": None, "stock_selector": None})
        known_urls.add(url)
        changed = True

        price_text = f" (şu an {price} TL)" if price is not None else ""
        send_message(bot_token, chat_id, f"✅ '{name}' takibe eklendi{price_text}.")

    return changed