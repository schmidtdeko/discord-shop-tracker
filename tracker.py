import os
import json
import requests

DISCORD_SHOP_URL = "https://discord.com/api/v9/collectibles-categories"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CACHE_FILE = "known_skus.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
}

def run():
    known_skus = set()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            known_skus = set(json.load(f))

    first_run = len(known_skus) == 0

    try:
        res = requests.get(DISCORD_SHOP_URL, headers=HEADERS, timeout=15)
        categories = res.json().get("categories", [])
    except Exception as e:
        print(f"Erro ao buscar API: {e}")
        return

    current_skus = set()
    new_items = []

    for cat in categories:
        cat_name = cat.get("name", "Geral")
        for prod in cat.get("products", []):
            sku_id = prod.get("sku_id")
            name = prod.get("name", "Sem Nome")
            summary = prod.get("summary", "")
            if sku_id:
                current_skus.add(sku_id)
                if not first_run and sku_id not in known_skus:
                    new_items.append((name, summary, cat_name, sku_id))

    if WEBHOOK_URL and new_items:
        for name, summary, cat_name, sku_id in new_items:
            payload = {
                "embeds": [{
                    "title": f"🛍️ Novo Item na Loja: {name}",
                    "description": summary or "Novo banner/item disponível!",
                    "color": 5793266,
                    "fields": [
                        {"name": "Categoria", "value": cat_name, "inline": True},
                        {"name": "SKU", "value": f"`{sku_id}`", "inline": True}
                    ]
                }]
            }
            requests.post(WEBHOOK_URL, json=payload)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(current_skus), f, indent=2)

if __name__ == "__main__":
    run()
