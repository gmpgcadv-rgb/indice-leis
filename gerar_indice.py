#!/usr/bin/env python3
"""
Gera o índice de busca do acervo ctresb/leis (cópia local) para o repositório
gmpgcadv-rgb/indice-leis.

Uso:
    python gerar_indice.py <pasta do acervo> <pasta de saída>
    ex.: python gerar_indice.py G:\\leis-main G:\\indice-leis

Saída (arquivos .jsonl.gz, uma norma por linha):
    federal.jsonl.gz          normas federais (leis, decretos-lei, MPs, decretos...)
    jurisprudencia.jsonl.gz   súmulas, OJs, temas, controle concentrado
    estruturas.jsonl.gz       títulos/capítulos/seções das normas grandes (CF, CLT,
                              códigos) com o intervalo de artigos de cada parte
    estaduais/<UF>.jsonl.gz   normas estaduais, por UF
    municipais/<UF>.jsonl.gz  normas municipais, por UF
    outros.jsonl.gz           demais pastas (reguladores, tratados...)
    meta.json                 data de geração, contagens, data mais recente de download

Campos de cada linha: p (caminho no ctresb/leis), t (título), tp (tipo),
n (número), d (data), e (ementa, ou início do texto quando não há ementa),
r (revogada: true/false/null), tr (tribunal), v (versão do texto), b (baixado_em).

Só lê o cabeçalho de cada arquivo (exceto nas normas grandes, para as estruturas).
Ignora pastas que começam com "_" ou ".", e as pastas assets, fonte, scripts.
"""
import gzip
import json
import os
import re
import sys
import time
from datetime import date

IGNORAR = {"assets", "fonte", "scripts", "node_modules"}
CAMPOS = {"titulo": "t", "tipo": "tp", "numero": "n", "data": "d", "ementa": "e",
          "revogada": "r", "tribunal": "tr", "versao_texto": "v", "baixado_em": "b"}
LIMITE_ESTRUTURA = 60_000          # bytes: normas maiores ganham índice de estrutura
CABECALHO_BYTES = 6_000
RESUMO_CHARS = 400

RE_TITULO = re.compile(r'^#{2,6}\s+(.+?)\s*$')
RE_PARTE = re.compile(r'^\**\s*((?:LIVRO|PARTE|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O)\b.*?)\s*\**\s*$')
RE_ART = re.compile(r'^\**\s*Art\.\s*(\d+(?:\.\d+)?(?:-[A-Z])?)', re.I)


def valor(v):
    v = v.strip()
    if v.startswith('"'):
        try:
            return json.loads(v)
        except Exception:
            return v.strip('"')
    if v in ("true", "false"):
        return v == "true"
    if v in ("null", "~", ""):
        return None
    return v


def ler_cabecalho(texto):
    """Devolve (dados, corpo) a partir do frontmatter YAML simples."""
    dados = {}
    if not texto.startswith("---"):
        return dados, texto
    fim = texto.find("\n---", 3)
    if fim < 0:
        return dados, texto
    for linha in texto[3:fim].splitlines():
        if ":" in linha and not linha.startswith(" "):
            k, v = linha.split(":", 1)
            k = k.strip()
            if k in CAMPOS:
                dados[CAMPOS[k]] = valor(v)
    corpo = texto[fim + 4:]
    return dados, corpo


def resumo(corpo):
    corpo = re.sub(r'(\w)-\n(\w)', r'\1\2', corpo)   # junta palavras quebradas no fim da linha
    linhas = [l.strip() for l in corpo.splitlines()]
    linhas = [l for l in linhas if l and not l.startswith("#")]
    t = " ".join(linhas)
    t = re.sub(r'\*+', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t[:RESUMO_CHARS]


def estrutura(caminho_rel, texto):
    """Partes (título, capítulo, seção...) com o primeiro e o último artigo."""
    partes, atual = [], None
    hierarquia = []
    for linha in texto.splitlines():
        m = RE_TITULO.match(linha) or RE_PARTE.match(linha)
        if m:
            nome = re.sub(r'\*+', '', m.group(1)).strip()
            if len(nome) > 200 or not re.match(r'(LIVRO|PARTE|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O|Se[çc][ãa]o|Cap[íi]tulo|T[íi]tulo|Livro|Parte)', nome):
                continue
            nivel = nome.split()[0].upper()
            ordem = ["LIVRO", "PARTE", "TÍTULO", "TITULO", "CAPÍTULO", "CAPITULO", "SEÇÃO", "SECAO", "SUBSEÇÃO", "SUBSECAO"]
            pos = ordem.index(nivel) if nivel in ordem else 9
            hierarquia = [h for h in hierarquia if h[0] < pos] + [(pos, nome)]
            atual = {"p": caminho_rel, "parte": " > ".join(h[1] for h in hierarquia), "de": None, "ate": None}
            partes.append(atual)
            continue
        a = RE_ART.match(linha)
        if a and atual is not None:
            if atual["de"] is None:
                atual["de"] = a.group(1)
            atual["ate"] = a.group(1)
    return [p for p in partes if p["de"]]


def grupo(rel):
    partes = rel.split("/")
    if len(partes) == 1:
        return "federal"            # constituicao.md e outros na raiz
    raiz = partes[0]
    if raiz == "federal":
        return "federal"
    if raiz == "jurisprudencia":
        return "jurisprudencia"
    if raiz in ("estaduais", "municipais") and len(partes) > 2:
        return f"{raiz}/{partes[1].upper()}"
    return "outros"


def percorrer(base):
    pilha = [base]
    while pilha:
        d = pilha.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    if e.name.startswith((".", "_")) or e.name in IGNORAR:
                        continue
                    if e.is_dir(follow_symlinks=False):
                        pilha.append(e.path)
                    elif e.name.endswith(".md") and e.is_file(follow_symlinks=False):
                        yield e
        except OSError as erro:
            print(f"  aviso: não foi possível ler {d}: {erro}", file=sys.stderr)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    base, saida = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    if not os.path.isfile(os.path.join(base, "constituicao.md")):
        print("A pasta do acervo deve conter constituicao.md (ex.: G:\\leis-main).")
        sys.exit(1)
    os.makedirs(saida, exist_ok=True)
    ignorar_raiz = {"README.md", "COBERTURA.md", "PROGRESSO.md", "WORKLOG.md", "LICENSE.md"}

    arquivos, contagem, erros = {}, {}, 0
    estruturas = []
    ultimo_download = ""
    inicio = time.time()

    def escritor(g):
        if g not in arquivos:
            caminho = os.path.join(saida, g + ".jsonl.gz")
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            arquivos[g] = gzip.open(caminho, "wt", encoding="utf-8", compresslevel=9)
            contagem[g] = 0
        return arquivos[g]

    total = 0
    for e in percorrer(base):
        rel = os.path.relpath(e.path, base).replace(os.sep, "/")
        if "/" not in rel and rel in ignorar_raiz:
            continue
        try:
            grande = e.stat().st_size > LIMITE_ESTRUTURA
            with open(e.path, "r", encoding="utf-8", errors="replace") as f:
                texto = f.read() if grande else f.read(CABECALHO_BYTES)
        except OSError:
            erros += 1
            continue
        dados, corpo = ler_cabecalho(texto)
        if not dados.get("t"):
            h1 = re.search(r'^# (.+)$', corpo, re.M)
            dados["t"] = h1.group(1).strip() if h1 else rel.rsplit("/", 1)[-1][:-3]
        if not dados.get("e"):
            dados["e"] = resumo(corpo[:CABECALHO_BYTES])
        dados = {"p": rel, **{k: v for k, v in dados.items() if v not in (None, "")}}
        if isinstance(dados.get("b"), str) and dados["b"] > ultimo_download:
            ultimo_download = dados["b"]
        g = grupo(rel)
        escritor(g).write(json.dumps(dados, ensure_ascii=False, default=str) + "\n")
        contagem[g] += 1
        if grande and (g in ("federal", "jurisprudencia") or rel == "constituicao.md"):
            estruturas.extend(estrutura(rel, texto))
        total += 1
        if total % 20000 == 0:
            print(f"  {total:,} arquivos lidos ({time.time() - inicio:.0f}s)")

    for f in arquivos.values():
        f.close()
    with gzip.open(os.path.join(saida, "estruturas.jsonl.gz"), "wt", encoding="utf-8", compresslevel=9) as f:
        for s in estruturas:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    meta = {
        "fonte": "https://github.com/ctresb/leis",
        "raw": "https://raw.githubusercontent.com/ctresb/leis/main/<p>",
        "gerado_em": date.today().isoformat(),
        "download_mais_recente_no_acervo": ultimo_download,
        "total_normas": total,
        "partes_de_estrutura": len(estruturas),
        "arquivos": {g + ".jsonl.gz": n for g, n in sorted(contagem.items())},
        "erros_de_leitura": erros,
        "campos": {"p": "caminho", "t": "título", "tp": "tipo", "n": "número", "d": "data",
                    "e": "ementa ou início do texto", "r": "revogada", "tr": "tribunal",
                    "v": "versão do texto", "b": "baixado_em"},
    }
    with open(os.path.join(saida, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Pronto: {total:,} normas, {len(estruturas):,} partes de estrutura, "
          f"{erros} erros, {time.time() - inicio:.0f}s. Saída em {saida}")


if __name__ == "__main__":
    main()
