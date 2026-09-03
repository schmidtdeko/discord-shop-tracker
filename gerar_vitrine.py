import json
from soundcloud import Soundcloud

# Inicializa o cliente da nova biblioteca v2
client = Soundcloud()

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
            # Resolve a URL do perfil para pegar o ID interno do usuário
            user = client.resolve(url)
            
            # Busca a faixa mais recente usando o ID do usuário
            tracks = client.get_user_tracks(user.id, limit=1)
            
            for track in tracks:
                # Trata a data de criação
                data_formatada = track.created_at.strftime("%Y-%m-%d") if track.created_at else "1970-01-01"
                
                vitrine.append({
                    "artista": user.username,
                    "titulo": track.title,
                    "url": track.permalink_url,
                    "capa": track.artwork_url or "",
                    "data": data_formatada
                })
                print(f"Sucesso: {track.title} adicionado.")
        except Exception as e:
            print(f"Erro ao processar {url}: {e}")

    # Ordena da música mais nova para a mais antiga
    vitrine_ordenada = sorted(vitrine, key=lambda x: x["data"], reverse=True)

    with open("vitrine.json", "w", encoding="utf-8") as f:
        json.dump(vitrine_ordenada, f, indent=2, ensure_ascii=False)
    
    print(f"Vitrine gerada com {len(vitrine_ordenada)} faixas.")

if __name__ == "__main__":
    coletar_lancamentos()
