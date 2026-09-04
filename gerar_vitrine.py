import csv
import json
import os
import re
import sys
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


def aviso(titulo, texto):
    """Annotation de aviso: aparece no resumo da execucao no GitHub Actions."""
    print(f"::warning title={titulo}::{texto}")


def erro(texto):
    """Annotation de erro: destaca a linha no resumo da execucao."""
    print(f"::error::{texto}")

# Mesmo numero de vagas para todo mundo: quem sobe mais musica nao ganha
# mais espaco na vitrine por isso. 0 desliga o teto.
FAIXAS_POR_ARTISTA = 5

# Tamanho de pagina da API do SoundCloud. ATENCAO: o `limit` do
# get_user_tracks NAO limita o total - ele e o tamanho da pagina, e o
# gerador pagina o perfil inteiro. Quem corta de verdade e o
# FAIXAS_POR_ARTISTA, aplicado depois de ordenar por data.
PAGINA_SOUNDCLOUD = 50


def limpar_url(url):
    """Devolve uma URL de perfil que o resolve() aceite.

    O resolve() do SoundCloud EXIGE o esquema: 'soundcloud.com/artista'
    devolve None em silencio, so 'https://soundcloud.com/artista' funciona.
    E quem preenche formulario cola sem https, com www., com m. de mobile e
    com parametro de rastreio na cola.
    """
    u = url.strip().strip('<>"\'')
    u = u.split("?")[0].split("#")[0].rstrip("/")
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^(www\.|m\.|mobile\.)", "", u, flags=re.I)
    return "https://" + u


def normalizar(url):
    """Chave de comparacao, pra nao repetir o mesmo perfil vindo de duas fontes."""
    return re.sub(r"^https://", "", limpar_url(url).lower())


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
    for i, linha in enumerate(csv.reader(linhas)):
        if i == 0:
            continue  # cabecalho da planilha de respostas

        url = extrair_url(linha)
        if url:
            achados.append(url)
        elif any(c.strip() for c in linha):
            # Inscricao preenchida sem link reconhecivel: avisa em vez de
            # descartar calado, pra dar pra falar com a pessoa.
            aviso("Inscricao sem link do SoundCloud", " | ".join(linha))
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
            aviso(f"Fonte de perfis indisponivel: {origem}", str(e))
            continue

        novos = 0
        for url in achados:
            limpa = limpar_url(url)
            chave = normalizar(limpa)
            if chave and chave not in vistos:
                vistos.add(chave)
                perfis.append(limpa)
                novos += 1
        print(f"{origem}: {len(achados)} linhas com soundcloud.com, {novos} perfis novos.")

    return perfis


def coletar_lancamentos():
    perfis = carregar_perfis()
    if not perfis:
        erro("Nenhum perfil para consultar: o artistas.txt e a planilha falharam os dois. "
             "O vitrine.json atual foi mantido.")
        sys.exit(1)

    vitrine = []
    falhas = []
    for url in perfis:
        try:
            print(f"Buscando: {url}")
            user = client.resolve(url)

            faixas = []
            for track in client.get_user_tracks(user.id, limit=PAGINA_SOUNDCLOUD):
                faixas.append({
                    "artista": user.username,
                    # avatar e perfil vem na MESMA resposta do resolve(), sem
                    # requisicao extra - e o que deixa a vitrine mostrar gente
                    # em vez de so nome de arquivo.
                    "avatar": user.avatar_url or "",
                    "perfil": user.permalink_url or "",
                    "titulo": track.title,
                    "url": track.permalink_url,
                    "capa": track.artwork_url or "",
                    "data": track.created_at.strftime("%Y-%m-%d") if track.created_at else "1970-01-01",
                })
        except Exception as e:
            # Um perfil ruim (link errado no formulario, conta apagada) nao pode
            # derrubar a vitrine dos outros: vira aviso visivel e o fluxo segue.
            falhas.append(url)
            aviso("Perfil ignorado", f"{url} -> {e}")
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

    # Nunca sobrescreve a vitrine com lista vazia (SoundCloud fora do ar, ou a
    # soundcloud-v2 quebrada porque a API nao oficial mudou). Aqui falha de
    # proposito: o vitrine.json antigo continua no ar e o GitHub manda e-mail.
    if not vitrine:
        erro(f"Nenhuma faixa coletada de {len(perfis)} perfis. A API do SoundCloud pode ter "
             "mudado (soundcloud-v2 desatualizada). O vitrine.json atual foi mantido.")
        sys.exit(1)

    vitrine.sort(key=lambda x: x["data"], reverse=True)

    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(vitrine, f, indent=2, ensure_ascii=False)

    por_artista = {}
    for item in vitrine:
        por_artista[item["artista"]] = por_artista.get(item["artista"], 0) + 1

    print(f"{len(vitrine)} faixas de {len(por_artista)} artistas gravadas em {SAIDA}.")
    for artista, quantas in sorted(por_artista.items(), key=lambda kv: -kv[1]):
        print(f"  {quantas:>2}x {artista}")

    if falhas:
        aviso(
            f"{len(falhas)} de {len(perfis)} perfis nao entraram",
            "Confira se o link esta certo ou se a conta ainda existe: " + ", ".join(falhas),
        )


if __name__ == "__main__":
    coletar_lancamentos()
