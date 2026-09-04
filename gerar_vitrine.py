import csv
import json
import os
import re
import urllib.request

from soundcloud import SoundCloud

client = SoundCloud()

# Planilha de RESPOSTAS do formulario de inscricao, lida como CSV.
# Precisa estar compartilhada como "Qualquer pessoa com o link: Leitor",
# senao o export responde 401 e o script segue so com a lista do repo.
PLANILHA_ID = "1HVBQQ0fZsTBEE6hyIRrjfFaN-GTCY2bU-lbyNFaWyrM"
URL_DA_PLANILHA = f"https://docs.google.com/spreadsheets/d/{PLANILHA_ID}/export?format=csv"

# Lista fixa versionada no repo. As inscricoes do formulario entram somadas a ela.
ARQUIVO_BASE = "artistas.txt"

SAIDA = "vitrine.json"

# Mesmo numero de vagas para todo mundo: quem sobe mais musica nao ganha
# mais espaco na vitrine por isso. 0 desliga o teto.
FAIXAS_POR_ARTISTA = 5

# Tamanho de pagina da API do SoundCloud. ATENCAO: o `limit` do
# get_user_tracks NAO limita o total - ele e o tamanho da pagina, e o
# gerador pagina o perfil inteiro. Quem corta de verdade e o
# FAIXAS_POR_ARTISTA, aplicado depois de ordenar por data.
PAGINA_SOUNDCLOUD = 50


def normalizar(url):
    """Chave de comparacao, pra nao repetir o mesmo perfil vindo de duas fontes."""
    u = url.strip().split("?")[0].split("#")[0].rstrip("/").lower()
    return re.sub(r"^https?://(www\.)?", "", u)


def extrair_url(linha):
    """Primeira celula da linha que contenha um perfil do SoundCloud.

    A planilha e a de respostas do formulario (Timestamp, Nome do artista,
    Link do perfil), entao a coluna do link nao e fixa: varre a linha inteira
    em vez de assumir a coluna A.
    """
    for celula in linha:
        if "soundcloud.com" in celula.lower():
            return celula.strip()
    return None


def perfis_da_planilha():
    resposta = urllib.request.urlopen(URL_DA_PLANILHA, timeout=30)
    linhas = resposta.read().decode("utf-8").splitlines()

    achados = []
    for linha in csv.reader(linhas):
        url = extrair_url(linha)
        if url:
            achados.append(url)
    return achados


def perfis_do_arquivo():
    if not os.path.exists(ARQUIVO_BASE):
        return []

    with open(ARQUIVO_BASE, encoding="utf-8") as f:
        return [linha.strip() for linha in f if "soundcloud.com" in linha.lower()]


def carregar_perfis():
    """Junta a lista do repo com as inscricoes do formulario, sem repetir perfil."""
    perfis, vistos = [], set()

    for origem, captador in (("repo", perfis_do_arquivo), ("formulario", perfis_da_planilha)):
        try:
            achados = captador()
        except Exception as e:
            print(f"Erro ao ler os perfis do {origem}: {e}")
            continue

        novos = 0
        for url in achados:
            chave = normalizar(url)
            if chave and chave not in vistos:
                vistos.add(chave)
                perfis.append(url)
                novos += 1
        print(f"{origem}: {len(achados)} linhas com soundcloud.com, {novos} perfis novos.")

    return perfis


def coletar_lancamentos():
    perfis = carregar_perfis()
    if not perfis:
        print("Nenhum perfil para consultar. Mantendo o vitrine.json atual.")
        return

    vitrine = []
    for url in perfis:
        try:
            print(f"Buscando: {url}")
            user = client.resolve(url)

            faixas = []
            for track in client.get_user_tracks(user.id, limit=PAGINA_SOUNDCLOUD):
                faixas.append({
                    "artista": user.username,
                    "titulo": track.title,
                    "url": track.permalink_url,
                    "capa": track.artwork_url or "",
                    "data": track.created_at.strftime("%Y-%m-%d") if track.created_at else "1970-01-01",
                })
        except Exception as e:
            print(f"Erro ao processar {url}: {e}")
            continue

        # A API nao devolve as faixas em ordem cronologica, entao ordena antes
        # de cortar - senao as vagas do artista sao preenchidas com faixas
        # aleatorias do perfil em vez das mais recentes.
        faixas.sort(key=lambda f: f["data"], reverse=True)
        if FAIXAS_POR_ARTISTA > 0:
            achadas = len(faixas)
            faixas = faixas[:FAIXAS_POR_ARTISTA]
            print(f"  {user.username}: {achadas} no perfil, {len(faixas)} na vitrine")

        vitrine.extend(faixas)

    # Nunca sobrescreve a vitrine com lista vazia (SoundCloud fora do ar, por exemplo).
    if not vitrine:
        print("Nenhuma faixa coletada. Mantendo o vitrine.json atual.")
        return

    vitrine.sort(key=lambda x: x["data"], reverse=True)

    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(vitrine, f, indent=2, ensure_ascii=False)

    por_artista = {}
    for item in vitrine:
        por_artista[item["artista"]] = por_artista.get(item["artista"], 0) + 1

    print(f"{len(vitrine)} faixas de {len(por_artista)} artistas gravadas em {SAIDA}.")
    for artista, quantas in sorted(por_artista.items(), key=lambda kv: -kv[1]):
        print(f"  {quantas:>2}x {artista}")


if __name__ == "__main__":
    coletar_lancamentos()
