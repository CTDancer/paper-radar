# Paper Radar

Paper Radar is a Python repository for discovering, ranking, summarizing, and archiving the daily research papers most relevant to generative modeling, optimization, and AI for drug discovery/design.

The main workflow writes a Markdown report to `../Daily_Papers/YYYY-MM-DD.md` with up to 10 top papers, near misses, and a search log.

## Install

```bash
cd paper-radar
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,llm]"
```

The current implementation intentionally works in degraded mode with only the Python standard library. Optional packages are declared for normal development and future extensions.

## Configure API Keys

Copy `.env.example` to `.env` and fill in what you have:

```bash
OPENAI_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=
NCBI_EMAIL=
NCBI_API_KEY=
```

The system still runs if optional keys are missing. Without `OPENAI_API_KEY`, summaries are conservative degraded-mode notes based only on title, abstract, and metadata. Passing `--no-llm` forces this mode even if an API key is present. For Codex Automation, you do not need an OpenAI API key: run `daily-candidates`, then let the Codex automation model write the final Markdown report from the candidate packet. Degraded fallback summaries are allowed only for debugging artifacts, never for the final report. The optional `.env` API path is only for users who explicitly want the Python CLI itself to call an LLM API.

## Edit Topics

Edit `config/topics.yaml` to adjust weighted topic groups. The file is JSON-compatible YAML so it can be read without requiring PyYAML.

Useful knobs:

- Add terms to a topic group to increase recall.
- Increase a group weight to make it more prominent in ranking.
- Keep DNA/RNA terms low priority unless they include transferable generative modeling or optimization ideas.

Ranking weights live in `config/ranking.yaml`.

## Run

Full daily workflow:

```bash
python -m paper_radar.cli daily-candidates --lookback-days 3 --top-k 30
```

Installed console command:

```bash
paper-radar daily --lookback-days 3 --top-k 10
```

Fetch-only development command:

```bash
python -m paper_radar.cli fetch --lookback-days 3
```

Weekly placeholder:

```bash
python -m paper_radar.cli weekly --start 2026-06-06 --end 2026-06-12
```

## Data Sources

Implemented modular fetchers:

- arXiv Atom API
- OpenAlex Works API
- Semantic Scholar Graph API
- PubMed / NCBI E-utilities
- Europe PMC REST API

Fetchers use APIs rather than scraping. They fail softly so one unavailable source does not break the whole daily run.

## Ranking

Ranking is transparent and two-stage-ready:

1. Deterministic scoring uses topic matches, title/abstract relevance, recency, source credibility, citation signal, code availability, and penalties.
2. LLM reranking is intentionally wired as a later stage for only the top deterministic candidate pool. The current implementation does not yet let the LLM reorder papers; it records `LLM-reranked candidates: 0`.

The deterministic ranker prefers papers with new methods, objectives, benchmarks, datasets, or transferable conceptual perspectives. It penalizes weakly relevant papers, review/survey papers, and DNA/RNA-only papers unless they contain transferable modeling or optimization ideas. The daily command first selects strict-threshold papers, then backfills from a lower plausible-candidate tier. If needed, it finally fills from the best remaining fetched candidates so the report reaches `--top-k` whenever at least that many deduplicated candidates exist.

## Summaries

LLM summarization is routed through `paper_radar/llm/client.py`. If `OPENAI_API_KEY` is unavailable or the request fails, Paper Radar writes conservative fallback summaries and clearly notes that method details, experiments, and limitations are unclear from metadata alone.

PDF text extraction is not implemented yet. Initial summaries use title, abstract, and metadata only.

## Tests

This repo uses `unittest` so tests run even before development dependencies are installed:

```bash
python -m unittest discover -s tests
```

Covered behavior includes DOI/arXiv/fuzzy-title deduplication, ranking relevance, DNA/RNA penalties, report generation, and config loading.

## Codex Automation

Example automation prompt for the no-API Codex workflow:

```text
Use the $paper-radar skill.

Run my daily paper radar candidate generation for today with `daily-candidates --lookback-days 3 --top-k 30`. Then use Codex/GPT-5.5-High to rerank candidates and write the final Markdown report, using only the candidate metadata, abstracts, links, score rationales, and concerns. Focus on generative modeling, optimization methods, AI for drug discovery and design, and unusually insightful transferable ideas. Make sure the summaries use clear paragraphs and cover motivation, methods, experiments, innovation, weaknesses, and methodological, theoretical, or design insights. The `Methods` section should explain the complete method clearly and plainly enough that I can understand the paper's approach from the summary alone.
```

For local Codex project automations, the machine should be powered on, Codex should be running, and the selected project should be available on disk.

## Known Limitations

- LLM reranking is not yet implemented; the deterministic stage produces the final order.
- Python-side PDF extraction is not yet implemented; Codex-mode final summaries should use the candidate packet and linked sources where accessible.
- Source APIs may return sparse metadata or enforce rate limits.
- The weekly command is currently a placeholder that creates a TODO report.
