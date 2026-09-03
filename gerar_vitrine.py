import json
import urllib.request
from soundcloud import SoundCloud

client = SoundCloud()

# Cole o link do CSV gerado pelo Google Sheets aqui dentro das aspas
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQyWcPc0JYomI3tNYzlfnf3I6GLvCKnVDb38UEpoJfhLnptUc4H5Zxx6Qkx-fb65iEWcRG5HMRxtYgv/pub?output=csv"

def coletar_lancamentos():
    vitrine = []
    
    try:
        print("Lendo artistas da planilha do Google...")
        resposta = urllib.request.urlopen(URL_DA_PLANILHA)
        linhas = resposta.read().decode('utf-8').splitlines()
        
        # Pega só as linhas que realmente são links do SoundCloud
        perfis = [linha.strip() for linha in linhas if "soundcloud.com" in linha]
        print(f"Encontrados {len(perfis)} perfis na planilha.")
    except Exception as e:
        print(f"Erro ao ler a planilha: {e}")
        return

    for url in perfis:
        try:
            print(f"Buscando: {url}")
            user = client.resolve(url)
            
            tracks = client.get_user_tracks(user.id, limit=1)
            
            for track in tracks:
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

    vitrine_ordenada = sorted(vitrine, key=lambda x: x["data"], reverse=True)

    with open("vitrine.json", "w", encoding="utf-8") as f:
        json.dump(vitrine_ordenada, f, indent=2, ensure_ascii=False)
    
    print(f"Vitrine gerada com {len(vitrine_ordenada)} faixas.")

if __name__ == "__main__":
    coletar_lancamentos()
