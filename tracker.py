import os
import json
import requests

# Espelho público e atualizado da loja do Discord (sem bloqueio de bot/403)
SHOP_DATA_URL = "https://raw.githubusercontent.com/discord-datamining/discord-datamining/master/collectibles.json"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CACHE_FILE = "known_skus.json"

def run():
    known_skus = set()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    known_skus = set(content)
        except Exception:
            known_skus = set()

    first_run = len(known_skus) == 0

    try:
        res = requests.get(SHOP_DATA_URL, timeout=15)
        print(f"Status da resposta: {res.status_code}")
        
        if res.status_code != 200:
            print(f"Erro na requisição: {res.text[:300]}")
            return

        data = res.json()
        categories = data.get("categories", []) if isinstance(data, dict) else data

    except Exception as e:
        print(f"Exceção ao consultar API: {e}")
        return

    current_skus = set()
    new_items = []

    for cat in categories:
        cat_name = cat.get("name", "Geral")
        products = cat.get("products", [])
        
        for prod in products:
            sku_id = str(prod.get("sku_id", prod.get("id", "")))
            name = prod.get("name", "Sem Nome")
            summary = prod.get("summary", "")
            
            if sku_id:
                current_skus.add(sku_id)
                if not first_run and sku_id not in known_skus:
                    new_items.append((name, summary, cat_name, sku_id))

    print(f"Total de SKUs encontrados: {len(current_skus)}")

    # Envia notificação apenas se houver itens novos
    if WEBHOOK_URL and new_items:
        for name, summary, cat_name, sku_id in new_items:
            payload = {
                "embeds": [{
                    "title": f"🛍️ Novo Item na Loja do Discord: {name}",
                    "description": summary or "Novo banner/item disponível na loja!",
                    "color": 5793266,
                    "fields": [
                        {"name": "Categoria", "value": cat_name, "inline": True},
                        {"name": "SKU", "value": f"`{sku_id}`", "inline": True}
                    ],
                    "footer": {"text": "Discord Shop Tracker"}
                }]
            }
            requests.post(WEBHOOK_URL, json=payload)

    # Salva o arquivo de estado
    if current_skus:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(current_skus), f, indent=2)

if __name__ == "__main__":
    run()
