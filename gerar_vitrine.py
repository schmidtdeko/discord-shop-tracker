import json
from sclib import SoundcloudAPI

# Inicializa a API não oficial
api = SoundcloudAPI()

PERFIS = [
    "https://soundcloud.com/dksoundresearch",
    "https://soundcloud.com/gabriel-walter-iles",
    "https://soundcloud.com/leomorini",
    "https://soundcloud.com/elrafatavares",
    "https://soundcloud.com/b0nmusiq",
    "https://soundcloud.com/djschure",
    "https://soundcloud.com/mosersemh"
]

def coletar_lancamentos():
    vitrine = []
    
    for url in PERFIS:
        try:
            print(f"Buscando: {url}")
            # Resolve a URL do perfil para um objeto de Usuário
            usuario = api.resolve(url)
            
            # Pega as 3 faixas mais recentes (evita lotar o front)
            faixas = list(usuario.get_tracks(limit=3))
            
            for faixa in faixas:
                vitrine.append({
                    "artista": usuario.username,
                    "titulo": faixa.title,
                    "url": faixa.permalink_url,
                    "capa": faixa.artwork_url,
                    "data": faixa.created_at.strftime("%Y-%m-%d")
                })
        except Exception as e:
            print(f"Erro ao processar {url}: {e}")

    # Ordena tudo da faixa mais nova para a mais antiga
    vitrine_ordenada = sorted(vitrine, key=lambda x: x["data"], reverse=True)

    with open("vitrine.json", "w", encoding="utf-8") as f:
        json.dump(vitrine_ordenada, f, indent=2, ensure_ascii=False)
    
    print(f"Vitrine gerada com {len(vitrine_ordenada)} faixas.")

if __name__ == "__main__":
    coletar_lancamentos()
