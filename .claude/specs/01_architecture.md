# AI Research Agent — LangGraph Build Spec

You are implementing the backend LangGraph architecture for an AI Research Agent.
This document is the complete spec. Follow it exactly — do not invent new state
fields, endpoints, or modes not listed here. Where files already exist (listed in
"Existing Files" below), extend them rather than rewriting from scratch.

---

## 1. Project Summary

A research assistant with three UI panels: **Sources** (persistent uploaded
knowledge), **Chat** (conversation with mode toggles), **Get Articles** (paper
search). The user explicitly controls which knowledge the assistant uses via two
toggle switches — there is no automatic mode detection.

---

## 2. UI Behavior (must map 1:1 to backend state)

- Header shows two toggles: `Sources [ON/OFF]`, `Articles [ON/OFF]`, and a live
  `Current Mode` label.
- Toggle combinations map to exactly 4 modes:

| Sources | Articles | knowledge_mode |
|---|---|---|
| OFF | OFF | `general` |
| ON | OFF | `sources` |
| OFF | ON | `article` |
| ON | ON | `hybrid` |

- Mode switching is **never automatic**. The backend must never override
  `knowledge_mode` sent by the frontend — it only validates whether the mode is
  actually usable (see Supervisor rules below) and falls back to `general` if the
  toggled mode has no usable data.
- Chat history is **shared across all modes** — switching toggles mid-conversation
  does not clear or branch the history, it only changes what gets retrieved for
  the next turn.
- Every assistant answer must display which sources grounded it (e.g. "Answer
  generated using ✓ LangGraph.pdf"), taken from `active_sources_used`.
- Every answer is followed by exactly 3–5 clickable follow-up question chips.
  Clicking one sends its text as the next user query, through the same `/chat`
  flow.
- Uploaded sources show in the left panel immediately on upload, but must be
  visually marked (e.g. spinner/"processing") until backend status is `ready`.
  Do not allow a source to be counted toward `sources` or `hybrid` mode retrieval
  until it is `ready` — this prevents querying an empty/partial vector index.
- Selecting a paper in Get Articles sets `selected_article` but does NOT
  auto-enable the `Articles` toggle — the user still flips it on manually.
- Selecting a new article replaces the previous `selected_article` entirely; the
  old article's temporary vector store should be discarded.

---

## 3. Tech Stack

- Orchestration: **LangGraph**
- LLM integration: **LangChain** (`langchain_openai.ChatOpenAI` in existing code,
  swappable)
- Backend: **FastAPI**
- Vector store: **FAISS or Chroma** — two separate stores/namespaces:
  1. Persistent store for `uploaded_sources` (grows over the session)
  2. Temporary store for `selected_article` (fully replaced on each new
     selection)
- Embedding model: `BAAI/bge-small-en-v1.5` or equivalent
- Article search providers: arXiv, Semantic Scholar, Wikipedia

---

## 4. State Schema (already implemented — see `state.py`)

```python
class SourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

class UploadedSource(TypedDict):
    id: str
    filename: str
    source_type: Literal["pdf", "wikipedia"]
    status: SourceStatus
    vector_ref: str | None

class SelectedArticle(TypedDict):
    id: str
    title: str
    authors: list[str]
    status: SourceStatus
    vector_ref: str | None

class ChatTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    mode: str | None
    grounded_in: list[str]

class ResearchState(TypedDict):
    query: str
    knowledge_mode: Literal["general", "sources", "article", "hybrid"]
    chat_history: list[ChatTurn]
    uploaded_sources: list[UploadedSource]
    selected_article: SelectedArticle | None
    article_results: list[dict]
    retrieved_chunks: list[dict]
    article_chunks: list[dict]
    merged_context: list[dict]
    answer: str
    followup_questions: list[str]
    active_sources_used: list[str]
```

Do not rename or remove any field. If you need new fields, append them and note
why in a comment.

---

## 5. Graph Structure (already implemented — see `nodes.py`, `graph.py`)

```
Entry → supervisor
supervisor → (conditional: route_by_mode) → general_chat | retrieval | article_retrieval | hybrid_context
each of those four → response_generator
response_generator → followup_generator → END
```

### Node responsibilities

1. **`supervisor_node`** — never answers the user. Filters `uploaded_sources` to
   only `status == READY`; sets `selected_article = None` if its status isn't
   `READY`. This is the enforcement point for the "don't retrieve from
   unindexed sources" rule in section 2.

2. **`route_by_mode`** (conditional edge, not a node) — reads
   `state["knowledge_mode"]` plus whether ready sources/article exist post-filter.
   Falls back to `general_chat` if the requested mode has no usable data
   (e.g. user toggled `sources` ON but nothing is `ready` yet).

3. **`general_chat_node`** — no retrieval, LLM only. Sets `merged_context = []`
   and `active_sources_used = []`.

4. **`retrieval_node`** — retrieves top-k chunks from `uploaded_sources` only.
   Ignores `selected_article` entirely even if present.

5. **`article_retrieval_node`** — retrieves top-k chunks from
   `selected_article`'s temp store only. Ignores `uploaded_sources` entirely.

6. **`hybrid_context_node`** — retrieves from both stores independently
   (`retrieved_chunks` and `article_chunks` populated separately), then
   concatenates into `merged_context`. Do not blend the two retrieval calls
   into one query — they hit different vector stores.

7. **`response_generator_node`** — if `merged_context` is non-empty, generates
   the grounded answer via LLM using both `merged_context` and recent
   `chat_history` (last ~6 turns) in the prompt. Appends the turn to
   `chat_history` with `mode` and `grounded_in` populated — this is required for
   every turn, not optional, since the UI depends on it for the "grounded in"
   history annotation described in section 2.

8. **`followup_generator_node`** — separate LLM call. Input: `answer`,
   `knowledge_mode`. Output: exactly 3–5 short questions, no numbering, no
   markdown formatting — plain strings ready to render as chips.

---

## 6. Retrieval Layer (to build — `retrieval/`)

- `vector_store.py` — embedding client + FAISS/Chroma setup. Two logical
  collections as described in section 3.
- `sources_retriever.py` — implements
  `_retrieve_from_sources(query, sources, top_k) -> list[dict]`, called from
  `retrieval_node` and `hybrid_context_node`. Must scope retrieval to only the
  `vector_ref`s of the passed-in `sources` list (already pre-filtered to
  `READY` by the Supervisor) — do not re-check status here.
- `article_retriever.py` — implements
  `_retrieve_from_article(query, article, top_k) -> list[dict]`, scoped to
  `article["vector_ref"]`.
- Each returned chunk dict must include at minimum: `{"text": str,
  "source_name": str, "score": float}`. `source_name` is what populates
  `active_sources_used` in the nodes — must match the filename/title shown in
  the UI exactly.

---

## 7. Ingestion Layer (to build — `ingestion/`)

- `pdf_loader.py`, `wikipedia_loader.py` — extract raw text.
- `chunker.py` — splits into embeddable chunks (recursive character or
  token-based splitter).
- `source_processor.py` — background task run by the `/upload` and `/wiki`
  endpoints. Must transition status `pending → processing → ready` (or `error`
  on failure) and write the resulting `vector_ref` back onto the source record.
  This status transition is what the Supervisor and the UI's "processing"
  spinner depend on — do not skip straight to `ready`.

---

## 8. Article Search Layer (to build — `search/`)

- `arxiv_client.py` — **already implemented**, returns list of dicts:
  `{id, title, authors, abstract, publication_year, source, pdf_link,
  citation_count}`. Use this exact schema for the other two clients.
- `semantic_scholar_client.py` — same output schema, `source: "Semantic
  Scholar"`.
- `wikipedia_search_client.py` — same output schema, `source: "Wikipedia"`,
  `citation_count: None`.
- `article_ranker.py` — calls all three clients in parallel (e.g.
  `asyncio.gather` or `concurrent.futures.ThreadPoolExecutor` since the clients
  are currently synchronous), merges results, removes duplicates (compare
  normalized titles), ranks (recency + citation_count where available), returns
  top 10. This populates `article_results` in state / the `/articles` response.

---

## 9. FastAPI Endpoints (to build — `routers/`)

All request/response bodies should be Pydantic models mirroring the relevant
slice of `ResearchState`.

| Endpoint | Behavior |
|---|---|
| `POST /chat` | Build `ResearchState` from request + session store, invoke `research_graph`, return `{answer, followup_questions, active_sources_used, knowledge_mode}` |
| `POST /upload` | Save file, create `UploadedSource` with `status=PENDING`, kick off `source_processor` as a background task, return `{source_id, status}` immediately (do not block on processing) |
| `POST /wiki` | Same as `/upload` but for a Wikipedia URL |
| `GET /articles?topic=` | Call `article_ranker`, return top 10 |
| `POST /select-article` | Run Article Processing (download/parse/chunk/embed into temp store), set `selected_article`, status transitions same as `/upload` |
| `DELETE /source/{id}` | Remove from session store and drop its vectors from the persistent store |
| `GET /history` | Return `chat_history` for the session |

Session/state persistence: use an in-memory dict keyed by session id for now
(swap for Redis later) — `session_store.py`. Every endpoint reads/writes through
it so `chat_history` and `uploaded_sources` survive across requests within a
session.

---

## 10. Explicit Non-Goals / Constraints

- Do not implement automatic mode detection — this was deliberately replaced
  with explicit toggles. Do not add heuristics that override
  `knowledge_mode`.
- Do not merge the two vector stores into one collection — they must stay
  separable so `retrieval_node` and `article_retrieval_node` can query them
  independently.
- Do not skip the `PENDING → PROCESSING → READY` status lifecycle for sources,
  even for small/fast files — the UI's spinner and the Supervisor's filter both
  depend on this being real, not instantaneous.
- Keep `general_chat_node` free of any retrieval calls, even if sources exist —
  mode isolation must be exact per the decision table in section 2.

---

## 11. Existing Files (do not rewrite, extend if needed)

- `state.py` — `ResearchState` and related TypedDicts, final as specified above
- `nodes.py` — all 7 node functions + `route_by_mode`, retrieval helpers are
  stubs (`_retrieve_from_sources`, `_retrieve_from_article`) — implement these
  in `retrieval/` and import them in, don't reimplement inline
- `graph.py` — `build_research_graph()`, wiring is final
- `search/arxiv_client.py` — reference schema for the other two search clients

---

## 12. Acceptance Criteria

- `research_graph.invoke(state)` runs end-to-end for all 4 modes without error
  given a state with at least one `READY` source and one `READY` article.
- Toggling `sources` ON with zero ready sources falls back to `general` mode
  cleanly (no exception, no empty-context LLM call).
- `active_sources_used` and `chat_history[-1]["grounded_in"]` always match.
- `followup_questions` always has length 3–5.
- All three search clients return identically-shaped dicts, verified by a
  shared test asserting key equality across `arxiv_client`,
  `semantic_scholar_client`, and `wikipedia_search_client` outputs.