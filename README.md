# Índice do acervo de legislação (ctresb/leis)

Índice de busca do acervo [ctresb/leis](https://github.com/ctresb/leis), usado pelas skills jurídicas do escritório GMP | G&C (`consulta-legislacao`, `contestacao-trabalhista`, `acompanhamento-processo-trabalhista`).

O índice serve para **encontrar** a norma (por assunto, número, tipo ou tribunal). O texto que se cita é sempre lido no arquivo original do ctresb/leis, pelo link raw que cada resultado traz.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `federal.jsonl.gz` | Constituição e normas federais: caminho, título, tipo, número, data, ementa, revogada |
| `jurisprudencia.jsonl.gz` | Súmulas, OJs, temas e controle concentrado (TST, STF, STJ, TNU, TRF4...), com o início do enunciado |
| `estruturas.jsonl.gz` | Títulos, capítulos e seções das normas grandes (CF, CLT, códigos) com o intervalo de artigos de cada parte |
| `estaduais/<UF>.jsonl.gz`, `municipais/<UF>.jsonl.gz` | Normas estaduais e municipais, por UF |
| `meta.json` | Data de geração, contagens e data de download mais recente do acervo |
| `buscar.py` | Busca no índice (baixa os arquivos daqui na primeira vez) |
| `gerar_indice.py` | Gera o índice a partir de uma cópia local do ctresb/leis |

## Buscar

```
python3 buscar.py "intervalo intrajornada"
python3 buscar.py "jornada ônus prova" --em jurisprudencia
python3 buscar.py "piso salarial" --em estaduais/PR --vigentes
```

## Atualizar o índice

1. Atualizar a cópia local do acervo (de preferência `git pull` num clone do ctresb/leis).
2. `python gerar_indice.py G:\leis-main G:\indice-leis`
3. `git add -A && git commit -m "Atualiza índice" && git push`

O acervo ctresb/leis é distribuído sob licença MIT; este repositório contém apenas metadados derivados dele.
