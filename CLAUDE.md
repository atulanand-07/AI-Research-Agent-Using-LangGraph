# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A NotebookLM-style research assistant: a React (Vite) frontend talking to a FastAPI + LangGraph backend. Users upload PDFs / Wikipedia links as **sources**, search arXiv / Semantic Scholar / Wikipedia for **articles**, and chat in one of four knowledge modes (**General / RAG / Article / Hybrid**) — selected explicitly by two header toggles. The backend is an in-memory app: `SessionStore` + `InMemoryVectorStore`, no DB, no Redis, no real embeddings (256-dim hashed bag-of-words cosine via `sha256`).

The full design contract is in `.claude/specs/01_architecture.md` — read it before changing the graph, state schema, or mode table. The frontend↔backend integration is described in `.antigravitycli/plans/01_frontent _backend_integration.md`. A past prompt bug (general-mode refusal) is documented in `.antigravitycli/bug-fix/01_bug-fix.md` and is the reason `general_chat_node` uses `_build_general_prompt` rather than the shared `_build_prompt`.

## Common commands

All Python commands assume the project venv at `.venv\` (Windows) — the same path the `package.json` script uses.

```bash
# Frontend dev (Vite). Tries 5173, falls back to 5174 — see "Ports" below.
npm run dev

# Backend dev (uvicorn, :8000). CORS is open, so origin doesn't matter.
npm run dev:backend
# or directly:
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Backend tests (pytest, defaults — no conftest.py / pytest.ini)
.\.venv\Scripts\python.exe -m pytest backend\tests

# Run a single test file
.\.venv\Scripts\python.exe -m pytest backend\tests\test_graph.py

# Run a single test
.\.venv\Scripts\python.exe -m pytest backend\tests\test_graph.py::test_all_grounded_modes_invoke

# Frontend production build
npm run build
npm run preview
```

No linter, formatter, or type checker is configured. There is no `conftest.py`, `pytest.ini`, `pyproject.toml`, or `vite.config.*` checked in.

## Architecture

### Frontend — `src/`

- `index.html` + `src/main.jsx` — Vite root, mounts `<App />` in `#root`.
- `src/api.js` — Single `request()` wrapper that attaches an `x-session-id` UUID (from `localStorage` key `ai-research-agent-session-id`) to every fetch. Base URL: `import.meta.env.VITE_API_BASE_URL` else `http://127.0.0.1:8000`. Exposes `getSession`, `getHistory`, `sendChat`, `uploadPdf`, `addWikipediaSource`, `deleteSource`, `searchArticles`, `selectArticle`.
- `src/App.jsx` — Single-file React app (no router). Components: `Header`, `ToggleButtons`, `SourcesPanel` / `SourceCard`, `ChatPanel` / `ChatBubble` / `SuggestionChips`, `ArticlesPanel` / `SearchBar` / `PaperCard`.
  - The two header toggles derive `knowledge_mode` via `getKnowledgeMode(sourcesOn, articlesOn)` — table in the spec, section 2.
  - On mount: `getSession()` rehydrates `sources`, `selectedArticle`, `article_results`, `chat_history`.
  - **Polling**: while any source/article has `status === 'pending' | 'processing'`, the app re-calls `getSession()` every 1.5 s. There is no SSE / websocket.
  - Toggling does NOT clear history; switching modes mid-conversation keeps history and only changes what gets retrieved for the next turn.
- `src/styles.css` — Hand-written dark theme, 16 px radius, 25/50/25 grid workspace, fully responsive (tablet → 2-col, mobile → stacked). Tokens: bg `#1B1C1F`, card `#24262B`, border `#34373D`, accent `#4A90E2`, text `#FFFFFF`, secondary `#AEB4BE`, hover `#2D3037`.

### Backend — `backend/`

- `main.py` — FastAPI app, CORS `*`, mounts `chat_router`, `sources_router`, `articles_router`. `/` redirects to the Vite UI, `/health` returns `{status: "ok"}`.
- `state.py` — `ResearchState` TypedDict + `SourceStatus` enum. **Do not rename or remove fields.** The supervisor's `pending → processing → ready` filter and the UI's "grounded in" annotation both depend on the exact schema.
- `graph.py` — `build_research_graph()` assembles the LangGraph `StateGraph`:
  ```
  supervisor ──▶ route_by_mode ──▶ {general_chat | retrieval | article_retrieval | hybrid_context}
                                                 └─▶ response_generator ──▶ followup_generator ──▶ END
  ```
  A `_LinearFallbackGraph` mirrors the same flow if `langgraph` can't be imported, so tests run with partial deps.
- `nodes.py` — All 7 nodes + the `route_by_mode` conditional + the LLM wiring. Key invariants enforced here:
  - `supervisor_node` strips non-`READY` sources and drops a non-`READY` selected article.
  - `route_by_mode` downgrades to `general` if the requested mode has no usable data.
  - `general_chat_node` uses `_build_general_prompt` (history + question only); it must **not** include "answer only from context" instructions. The shared `_build_prompt` is for grounded modes only.
  - `hybrid_context_node` queries both stores independently and concatenates into `merged_context` — do not blend the two retrieval calls.
  - `response_generator_node` always appends an assistant `ChatTurn` to `chat_history` with `mode` and `grounded_in` populated; the UI's "Answer generated using …" line reads from this.
  - `followup_generator_node` ensures 3–5 questions, toping up from a fixed fallback list. `_clean_followups` strips the canned "could not reach Gemini" string so it never appears as a chip.
  - `_make_llm` returns `ChatGoogleGenerativeAI` if `GOOGLE_API_KEY` is set, else a deterministic `_FallbackLLM` stub. `_invoke_llm` swallows exceptions and substitutes a fixed "could not reach Gemini" message.
- `ingestion/` — `pdf_loader.py` (pypdf), `wikipedia_loader.py` (REST `/api/rest_v1/page/summary/`), `chunker.py` (1200-char windows, 150-char overlap), `source_processor.py` (background tasks that transition `pending → processing → ready` or `error`).
- `retrieval/` — `vector_store.py` (the in-memory hashed-BOW store; comment says FAISS can replace internals later), `sources_retriever.py` (scoped to passed `vector_ref`s), `article_retriever.py` (scoped to the article's `vector_ref`). Chunk dicts carry `text`, `source_name`, `score`, `vector_ref`, `chunk_id`; `source_name` populates `active_sources_used` and must match the UI filename/title exactly.
- `search/` — `arxiv_client.py` (Atom XML), `semantic_scholar_client.py`, `wikipedia_search_client.py`. All three return the same 8-key dict schema: `{id, title, authors, abstract, publication_year, source, pdf_link, citation_count}`. `article_ranker.py` fans out the three in a `ThreadPoolExecutor(3)`, dedupes by normalized title (keeps highest-ranked), sorts by `(year, citation_count)`, returns top 10. Per-provider errors are silently swallowed.
- `routers/` — `chat.py` (`POST /chat`, `GET /history`, `GET /session`), `sources.py` (`POST /upload`, `POST /wiki`, `DELETE /source/{id}`), `articles.py` (`GET /articles?topic=`, `POST /select-article`), `schemas.py` (Pydantic v2). All routers read `x-session-id` header (default `"default"`) and route through `session_store`.
- `session_store.py` — Thread-safe in-memory store. `get`, `update`, `build_state` (assembles a `ResearchState` from the session), `mutate_source` (patches one source's status / `vector_ref`). Resets on restart.

### Tests — `backend/tests/`

All tests `monkeypatch` a `DummyLLM` and stub `requests.get` where needed, so the suite is offline and deterministic. Coverage:
- `test_api.py` — `/chat` persists history; `/select-article` replaces the prior article.
- `test_graph.py` — all four modes, the `sources`-without-data → `general` fallback, follow-up count, and that the `general` prompt does not mention retrieved context.
- `test_retrieval.py` — retrieval scopes to passed `vector_ref`s.
- `test_search_schema.py` — the three search clients return the same key set; ranker dedupes by normalized title.

## Modes and the supervisor (don't break this)

| Sources | Articles | `knowledge_mode` | Required data |
|---|---|---|---|
| OFF | OFF | `general` | none |
| ON  | OFF | `sources` | ≥1 READY source |
| OFF | ON  | `article` | READY selected article |
| ON  | ON  | `hybrid` | ≥1 READY source AND READY selected article |

The supervisor silently downgrades any mode whose data is missing back to `general` and updates `state["knowledge_mode"]` accordingly. The `/chat` response echoes the **actual** `knowledge_mode` used so the UI can show "Mode: general" after a fallback. **The supervisor never overrides the user-chosen mode based on the data it finds — only on the data's absence.** Selecting an article does NOT auto-enable the `Articles` toggle.

## Environment / configuration

- `.env` (gitignored) carries `GOOGLE_API_KEY`. The backend uses it via `langchain-google-genai` (`gemini-2.5-flash-lite` by default, overridable with `GOOGLE_MODEL`, `GOOGLE_REQUEST_TIMEOUT`, `GOOGLE_RETRIES`).
- No `GOOGLE_API_KEY` → `_FallbackLLM` returns a fixed stub answer, so the app still runs end-to-end.
- **Quota**: the free-tier Gemini key frequently hits `RESOURCE_EXHAUSTED` (`backend.log` is full of 429s). Production-ish retry / backoff / model fallback is not implemented — `_invoke_llm` swallows the error and returns a canned message that is then filtered out of follow-up chips.
- Vite picks the first free port starting at 5173. Observed fallback: 5174. `main.py` redirects `/` to `http://127.0.0.1:5174` hard-coded.

## Conventions and gotchas

- Sessions are per-browser-tab (UUID in `localStorage`); two tabs = two isolated sessions.
- The two vector namespaces (`_sources`, `_articles` in `vector_store.py`) must stay separable — `retrieval_node` and `article_retrieval_node` query them independently.
- The `pending → processing → ready` lifecycle is required even for fast operations — the UI's spinner and the supervisor's `READY` filter both depend on it being a real transition, not instantaneous.
- `chat_history` is shared across all modes and never cleared when toggles change.
- `langgraph` and `pypdf` are optional at import time; the codebase has fallbacks so tests / dev work with partial installs. If you remove a fallback, add a test for the path it used to cover.
- No CI configured. No pre-commit hooks. No formatter.
