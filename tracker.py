import os
import json
import requests
import time

# Lista de URLs espelhos da comunidade para evitar erros 404 futuros
SHOP_DATA_URLS = [
    "https://raw.githubusercontent.com/discord-datamining/discord-datamining/master/collectibles.json", # Fonte anterior
    "https://api.merps.io/v1/collectibles", # Espelho 2
    "https://raw.githubusercontent.com/xnotwithit/discord-collectibles/main/collectibles.json" # Espelho 3
]

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CACHE_FILE = "known_skus.json"

# Headers padrões para simular acesso de navegador
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def load_from_urls():
    """Tenta carregar dados da loja de múltiplas URLs comunitárias."""
    for url in SHOP_DATA_URLS:
        try:
            print(f"Tentando carregar dados de: {url}")
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                print(f"Sucesso ao carregar de: {url}")
                return res.json()
            else:
                print(f"Falha na URL {url} (Status: {res.status_code})")
        except Exception as e:
            print(f"Erro ao tentar carregar da URL {url}: {e}")
            time.sleep(1) # Espera 1 segundo antes de tentar a próxima URL

    print("Todas as URLs comunitárias falharam.")
    return None

def run():
    # Carregar SKUs conhecidos
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
    print(f"Número de SKUs conhecidos no cache: {len(known_skus)}")

    # Obter dados da loja de terceiros
    data = load_from_urls()
    
    if data is None:
        print("Impossível obter dados da loja no momento. Finalizando execução.")
        return

    # Processar categorias (suportando diferentes formatos de API de terceiros)
    categories = []
    if isinstance(data, list):
        # Provavelmente dados do Merps ou lista direta
        if first_run: # Simular uma categoria falsa se for uma lista direta
            categories = [{"name": "Produtos da Loja", "products": data}]
        else:
            categories = [{"products": data}]
    elif isinstance(data, dict):
        # Provavelmente formato original do Discord {"categories": [...]}
        categories = data.get("categories", data.get("products", []))
    else:
        print("Formato de dados desconhecido. Finalizando.")
        return

    current_skus = set()
    new_items = []

    for cat in categories:
        if isinstance(cat, dict):
            cat_name = cat.get("name", cat.get("summary", "Produtos da Loja"))
            products = cat.get("products", [])
            
            for prod in products:
                # O ID pode ser sku_id (formato Discord) ou id (formato Merps)
                sku_id = str(prod.get("sku_id", prod.get("id", "")))
                name = prod.get("name", "Sem Nome")
                summary = prod.get("summary", "Novo banner/item disponível na loja!")
                
                if sku_id:
                    current_skus.add(sku_id)
                    # Verifica se é novo (não está na primeira execução e não está no cache)
                    if not first_run and sku_id not in known_skus:
                        new_items.append((name, summary, cat_name, sku_id))

    print(f"Total de SKUs encontrados nesta execução: {len(current_skus)}")

    # Envia notificação ao Discord apenas se houver itens novos
    if WEBHOOK_URL and new_items:
        print(f"Enviando {len(new_items)} notificações para o Discord...")
        for name, summary, cat_name, sku_id in new_items:
            payload = {
                "embeds": [{
                    "title": f"🛍️ Novo Item na Loja do Discord: {name}",
                    "description": summary,
                    "color": 5793266,
                    "fields": [
                        {"name": "Categoria", "value": cat_name, "inline": True},
                        {"name": "SKU (ID)", "value": f"`{sku_id}`", "inline": True}
                    ],
                    "footer": {"text": "Discord Shop Tracker"}
                }]
            }
            try:
                requests.post(WEBHOOK_URL, json=payload)
                print(f"Notificação enviada para: {name}")
            except Exception as e:
                print(f"Erro ao enviar notificação para {name}: {e}")

    # Salva a lista de SKUs conhecidos de volta para o cache
    if current_skus:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(current_skus), f, indent=2)
            print("Cache de SKUs atualizado.")

if __name__ == "__main__":
    run()
