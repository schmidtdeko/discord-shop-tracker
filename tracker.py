import os
import json
import requests

# Endpoint da loja do Discord
DISCORD_SHOP_URL = "https://discord.com/api/v9/collectibles-categories"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CACHE_FILE = "known_skus.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

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
        # Consulta com parâmetros de país
        res = requests.get(DISCORD_SHOP_URL, headers=HEADERS, params={"country_code": "BR"}, timeout=15)
        print(f"Status da resposta: {res.status_code}")
        
        if res.status_code != 200:
            print(f"Erro na requisição: {res.text[:300]}")
            return

        data = res.json()
        
        # Suporta retorno direto como lista ou dentro de objeto {"categories": [...]}
        if isinstance(data, list):
            categories = data
        elif isinstance(data, dict):
            categories = data.get("categories", data.get("products", []))
        else:
            categories = []

    except Exception as e:
        print(f"Exceção ao consultar API: {e}")
        return

    current_skus = set()
    new_items = []

    for cat in categories:
        cat_name = cat.get("name", "Geral")
        products = cat.get("products", [cat] if "sku_id" in cat else [])
        
        for prod in products:
            sku_id = prod.get("sku_id")
            name = prod.get("name", "Sem Nome")
            summary = prod.get("summary", "")
            
            if sku_id:
                current_skus.add(sku_id)
                if not first_run and sku_id not in known_skus:
                    new_items.append((name, summary, cat_name, sku_id))

    print(f"Total de SKUs encontrados: {len(current_skus)}")

    # Dispara alerta se houver novidade
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

    # Só sobrescreve se realmente encontrou itens para não zerar o arquivo
    if current_skus:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(current_skus), f, indent=2)

if __name__ == "__main__":
    run()
