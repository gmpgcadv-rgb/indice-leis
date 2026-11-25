#!/usr/bin/env python3
"""
Busca no índice do acervo ctresb/leis (repositório gmpgcadv-rgb/indice-leis).

Uso:
    python3 buscar.py "termos da busca" [--em federal,jurisprudencia,estruturas]
                      [--tipo "Súmula"] [--vigentes] [--max 20] [--indice <pasta local>]

Exemplos:
    python3 buscar.py "intervalo intrajornada"                 # federal + jurisprudência + estruturas
    python3 buscar.py "jornada ônus prova" --em jurisprudencia
    python3 buscar.py "vale-transporte" --vigentes
    python3 buscar.py "piso salarial" --em estaduais/PR

Todos os termos precisam aparecer (sem diferença de acento e maiúsculas) no título,
tipo, número, ementa ou parte da estrutura. Cada resultado traz o link raw do texto
integral no ctresb/leis, que deve ser lido antes de citar a norma.
"""
import argparse
import gzip
import io
import json
import os
import sys
import unicodedata
import urllib.request

REPO_RAW = "https://raw.githubusercontent.com/gmpgcadv-rgb/indice-leis/main/"
LEIS_RAW = "https://raw.githubusercontent.com/ctresb/leis/main/"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "indice-leis")


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def abrir(nome, pasta_local):
    if pasta_local:
        return gzip.open(os.path.join(pasta_local, nome), "rt", encoding="utf-8")
    os.makedirs(os.path.join(CACHE, os.path.dirname(nome)), exist_ok=True)
    destino = os.path.join(CACHE, nome)
    if not os.path.exists(destino):
        with urllib.request.urlopen(REPO_RAW + nome, timeout=120) as r:
            dados = r.read()
        with open(destino, "wb") as f:
            f.write(dados)
    return gzip.open(destino, "rt", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("termos")
    ap.add_argument("--em", default="federal,jurisprudencia,estruturas")
    ap.add_argument("--tipo")
    ap.add_argument("--vigentes", action="store_true", help="exclui normas marcadas como revogadas")
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--indice", help="pasta local com o índice (em vez de baixar)")
    a = ap.parse_args()

    termos = [norm(t) for t in a.termos.split() if t.strip()]
    tipo = norm(a.tipo) if a.tipo else None
    resultados = []
    for grupo in [g.strip() for g in a.em.split(",") if g.strip()]:
        nome = grupo + ".jsonl.gz"
        try:
            f = abrir(nome, a.indice)
        except Exception as e:
            print(f"[aviso] não consegui abrir {nome}: {e}", file=sys.stderr)
            continue
        with f:
            for linha in f:
                d = json.loads(linha)
                alvo = norm(" ".join(str(d.get(k, "")) for k in ("t", "tp", "n", "e", "parte", "tr")))
                if not all(t in alvo for t in termos):
                    continue
                if tipo and tipo not in norm(d.get("tp", "")):
                    continue
                if a.vigentes and d.get("r") is True:
                    continue
                # pontuação simples: termos no título/parte valem mais
                titulo = norm(str(d.get("t", "")) + " " + str(d.get("parte", "")))
                pontos = sum(3 for t in termos if t in titulo) + (1 if d.get("r") is False else 0)
                resultados.append((pontos, grupo, d))

    resultados.sort(key=lambda x: -x[0])
    for pontos, grupo, d in resultados[: a.max]:
        if grupo == "estruturas":
            print(f"- [estrutura] {d['p']}\n  {d['parte']} (arts. {d['de']} a {d['ate']})")
        else:
            rev = {True: "REVOGADA", False: "vigente"}.get(d.get("r"), "situação não informada")
            print(f"- {d.get('t')} | {d.get('tp', '')} | {d.get('d', '')} | {rev}\n  {str(d.get('e', ''))[:300]}")
        print(f"  {LEIS_RAW}{d['p']}")
    print(f"\n{len(resultados)} resultado(s); exibidos {min(len(resultados), a.max)}.")


if __name__ == "__main__":
    main()
