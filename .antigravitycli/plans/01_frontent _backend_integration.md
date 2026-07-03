
## Summary
Replace the current mock React behavior with real calls to the FastAPI backend while preserving the existing three-panel UI. The frontend will use one stable browser session id, map the two toggles to backend `knowledge_mode`, render backend chat/follow-up/grounding data, upload PDF/Wikipedia sources, search/select articles, and poll backend session state for processing status.

## Key Changes

- Add a small frontend API layer in `src/api.js`:
  - Base URL: `import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"`.
  - Generate/persist `x-session-id` in `localStorage`.
  - Implement helpers for `/chat`, `/upload`, `/wiki`, `/articles`, `/select-article`, `/source/{id}`, `/history`, and new `/session`.

- Add one backend read endpoint needed by the UI:
  - `GET /session` returns `{chat_history, uploaded_sources, selected_article, article_results}` for the current `x-session-id`.
  - This lets the Sources panel show real `pending | processing | ready | error` status and lets the UI refresh selected article state.
  - Keep existing endpoints unchanged.

- Replace mock frontend state in `src/App.jsx`:
  - Remove `initialSources`, static `papers`, fake `sendMessage`, and hardcoded follow-up chips.
  - Keep local UI state for `sourcesOn`, `articlesOn`, current draft, loading/error flags, selected article id, and search text.
  - Store messages as frontend-friendly objects derived from backend history and chat responses.
  - For assistant messages, render `active_sources_used` as “Answer generated using ...” and render backend `followup_questions` as clickable chips.

- Sources workflow:
  - Change “Add Sources” into a PDF file picker plus a Wikipedia URL input/action.
  - PDF upload sends `FormData` to `POST /upload`.
  - Wikipedia add sends `{url_or_topic}` to `POST /wiki`.
  - On success, immediately refresh `/session` and poll while any source is `pending` or `processing`.
  - Deleting a source calls `DELETE /source/{id}` then refreshes `/session`.

- Articles workflow:
  - Search input triggers `GET /articles?topic=...` on submit or debounced search.
  - Render backend article schema:
    - `title`
    - `authors`
    - `publication_year`
    - `source`
    - `abstract`
    - `citation_count`
  - Selecting a paper calls `POST /select-article` but does not auto-enable the Articles toggle.
  - Poll `/session` while selected article is `pending` or `processing`.

- Chat workflow:
  - `knowledge_mode` is computed exactly from toggles:
    - Sources OFF + Articles OFF: `general`
    - Sources ON + Articles OFF: `sources`
    - Sources OFF + Articles ON: `article`
    - Sources ON + Articles ON: `hybrid`
  - Sending a message calls `POST /chat` with `{query, knowledge_mode}`.
  - Add the user message optimistically, disable send while pending, then append backend assistant response.
  - If backend falls back to `general`, reflect returned `knowledge_mode` in the message metadata without changing the user’s toggles.

## Test Plan

- Backend:
  - Add API test for `GET /session`.
  - Re-run existing backend tests: `.\.venv\Scripts\python.exe -m pytest backend\tests`.

- Frontend:
  - Run `npm run build`.
  - Manually verify:
    - Chat works in `general`.
    - Follow-up chips send through `/chat`.
    - PDF upload appears immediately, then updates status.
    - Wikipedia add appears immediately, then updates status.
    - Articles search returns live results.
    - Selecting an article does not toggle Articles ON automatically.
    - Each toggle combination sends the correct `knowledge_mode`.
    - Source deletion updates the UI.

## Assumptions

- Backend runs on `http://127.0.0.1:8000`.
- Frontend runs on Vite `http://127.0.0.1:5173`.
- `.env` already contains `GOOGLE_API_KEY` for the backend.
- The current visual layout should be preserved; this is an integration pass, not a redesign.
- Add `GET /session` because current backend endpoints do not expose source/article processing status cleanly enough for the UI.
