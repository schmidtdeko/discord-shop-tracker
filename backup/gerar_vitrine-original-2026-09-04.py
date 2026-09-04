import json
import csv
import urllib.request
from soundcloud import SoundCloud

client = SoundCloud()

# Cole o link do CSV gerado pelo Google Sheets aqui
URL_DA_PLANILHA = "COLE_O_LINK_DO_CSV_AQUI"

def coletar_lancamentos():
    vitrine = []
    
    try:
        print("Lendo artistas da planilha...")
        resposta = urllib.request.urlopen(URL_DA_PLANILHA)
        linhas = resposta.read().decode('utf-8').splitlines()
        leitor = csv.reader(linhas)
        
        perfis = []
        for linha in leitor:
            if len(linha) > 0 and "soundcloud.com" in linha[0]:
                url = linha[0].strip()
                # Verifica se a coluna B tem a palavra "Sim"
                destaque = len(linha) > 1 and linha[1].strip().lower() == "sim"
                perfis.append({"url": url, "destaque": destaque})
                
    except Exception as e:
        print(f"Erro ao ler a planilha: {e}")
        return

    for perfil in perfis:
        url = perfil["url"]
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
                    "data": data_formatada,
                    "destaque": perfil["destaque"]
                })
        except Exception as e:
            print(f"Erro ao processar {url}: {e}")

    # Ordena: Destaques primeiro, depois os lançamentos mais recentes
    vitrine_ordenada = sorted(vitrine, key=lambda x: (x.get("destaque", False), x["data"]), reverse=True)

    with open("vitrine.json", "w", encoding="utf-8") as f:
        json.dump(vitrine_ordenada, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    coletar_lancamentos()
