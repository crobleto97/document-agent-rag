# Transport regulation assistant

An AI agent that answers questions about EU and Spanish road freight regulation and cites the exact article it relied on.
It flags when it is not sure instead of guessing, and an evaluation set measures how often it is right.

**Why:** operations and logistics teams lose time searching legal texts for answers such as how long a driver can drive in a week,
or who is liable when goods arrive damaged. Answers must be correct and traceable to the article.

## Documents

| Regulation | Topic | Languages |
|---|---|---|
| Regulation (EC) No 561/2006 (consolidated 31.12.2024) | Driving times, breaks and rest periods | EN, ES |
| Directive 2002/15/EC | Working time of mobile road transport workers | EN, ES |
| Ley 15/2009 (BOE consolidated text) | Contract for the carriage of goods by road | ES |

Texts come from EUR-Lex and the BOE open-data API and are not stored in this repo: the pipeline downloads them.

## Status

- [x] Stage 1: download, split into articles, embed and load into Postgres + pgvector
- [ ] Stage 2: baseline RAG and a ~50-question evaluation set
- [ ] Stage 3: LangGraph agent (route, retrieve, grade, answer with citations, verify, escalate)
- [ ] Stage 4: compare the agent against the baseline on the evaluation set

## Run it

Requirements: Python 3.10+, Docker Desktop.

```bash
cp .env.example .env              # set POSTGRES_PASSWORD and the same password in DATABASE_URL
docker compose up -d              # Postgres 16 + pgvector on localhost:5433
pip install -r requirements.txt

python src/download.py            # regulation texts -> data/raw/ (EUR-Lex may need a manual save, see below)
python src/parse.py               # one chunk per article -> data/processed/chunks.jsonl
python src/embed_load.py          # embeddings -> chunks table (first run downloads the model, ~1 GB)
python src/search.py "¿Cuántas horas puede conducir un camionero a la semana?"
```

**EUR-Lex bot check.** EUR-Lex sits behind an AWS WAF challenge and often answers scripts with HTTP 202 and an empty page.
`download.py` detects this and prints the URL and target file for each text it could not fetch: open the URL in a browser,
save it as "Web page, HTML only" with that file name, and re-run. The BOE API has no such check.

## Design choices

- **One chunk per article.** Legal questions are usually answered by a single article, and the article is what the answer must cite. Long articles are split on paragraph boundaries and keep their article number.
- **Multilingual embeddings, run locally.** `intfloat/multilingual-e5-base` puts Spanish and English in the same vector space, so a question in Spanish can find the English text and vice versa. No API cost.
- **pgvector instead of a dedicated vector database.** Vectors live next to the metadata in Postgres, with an HNSW index for cosine search. One service fewer to run.
- **Consolidated texts.** Regulation 561/2006 has been amended several times; the consolidated version is the one in force.

## Layout

```
src/sources.py       the regulations and their URLs
src/download.py      fetches the raw texts
src/parse.py         EUR-Lex HTML and BOE XML -> article chunks
src/embed_load.py    embeddings + load into pgvector
src/search.py        semantic search (the retrieval step)
tests/               parser tests on samples of the real formats
docker-compose.yml   Postgres + pgvector
```
