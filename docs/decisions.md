# Tech Decisions

Short architecture decision records explaining *why* the stack looks the way
it does. Optimised for someone reading the codebase for the first time.

---

## ADR-001: ChromaDB over Pinecone / pgvector

**Decision.** Use ChromaDB as the vector store.

**Why.**
- **Self-hostable.** Pinecone is a paid SaaS; ChromaDB runs in-process or
  alongside the API for free, which keeps the "zero-cost stack" promise in
  the README real.
- **Per-bot collection isolation.** ChromaDB makes it trivial to give each
  bot its own collection (`bot_{bot_id}`) — no schema design, no shared
  table to filter on every query.
- **Why not pgvector?** Supabase already hosts the relational data, so
  pgvector would have meant one less moving part. I chose ChromaDB because
  HNSW index tuning is exposed first-class and the client API is friendlier
  for prototyping. For a production deployment with >1M chunks I would
  re-evaluate pgvector.

**Trade-off.** Two databases to operate (Postgres for app data, Chroma for
vectors). Acceptable given how isolated the vector workload is.

---

## ADR-002: sentence-transformers (local) over OpenAI embeddings

**Decision.** Embed with `all-MiniLM-L6-v2` running locally.

**Why.**
- **Cost.** OpenAI `text-embedding-3-small` is cheap, but a knowledge base
  of a few thousand chunks plus every user query adds up. Local embeddings
  are free.
- **Latency.** No network round-trip on the query path.
- **Offline / privacy.** The whole RAG pipeline can run with no outbound
  calls — important for clients with sensitive documents.
- **384 dims is enough.** For document/question similarity at this scale,
  MiniLM is competitive with much larger models.

**Trade-off.** First-request cold start (~3s to load the model into memory).
Mitigated by lazy-loading a module-level singleton in `rag_pipeline.py`.

---

## ADR-003: Provider abstraction (Claude / OpenAI / Ollama)

**Decision.** Route every LLM call through `LLMClient` with a `provider`
field; switch via the `LLM_PROVIDER` env var.

**Why.**
- The same product needs to work in three deployment modes: paid hosted
  (Claude/OpenAI), self-hosted free (Ollama + LLaMA), and per-client mixes.
- Keeping API specifics out of `ai_engine.py` means the pipeline logic is
  the same regardless of model. Tests mock one interface, not three.
- Model names are configurable too (`CLAUDE_MODEL`, `OLLAMA_MODEL`, etc.) so
  upgrading models doesn't require a code change.

**Trade-off.** Lowest-common-denominator API surface. Provider-specific
features (Claude tool use, OpenAI structured outputs) aren't exposed. Fine
for the current pipeline; would need rework if we wanted those.

---

## ADR-004: Celery + Redis for ingestion, FastAPI BackgroundTasks for nothing

**Decision.** Document ingestion (parse → chunk → embed → upsert) runs on
Celery workers, not in-request.

**Why.**
- A 200-page PDF can produce 2000 chunks. Embedding them inline blocks the
  HTTP request for tens of seconds and risks timeouts behind a CDN.
- Celery gives us retries with backoff, a worker pool, and the option to
  scale ingestion independently of the API.
- **Why not FastAPI's built-in `BackgroundTasks`?** Those run in the same
  process as the request handler, so they don't survive restarts and don't
  scale across machines. Fine for emails, not for minutes-long jobs.

**Trade-off.** Two extra processes to manage (Redis + Celery worker).

---

## ADR-005: Confidence as `[Confidence: X/10]` self-report, with heuristic fallback

**Decision.** Ask the LLM to self-rate at the end of its answer; parse it
out with a regex; fall back to "0.7 if we found chunks, 0.3 if we didn't"
when the LLM forgets.

**Why.**
- A real calibration model is overkill for this product.
- Self-reported confidence correlates surprisingly well with answer
  correctness when the prompt is clear about it.
- The heuristic fallback ensures we never crash because the LLM didn't
  follow instructions — silent degradation, not a 500.

**Trade-off.** It's a *self-report*, so a confidently-wrong answer still
gets high confidence. Mitigated by also gating on intent (Complaints with
<70% confidence escalate even if the LLM says it's sure).

---

## ADR-006: Server-Sent Events for streaming, WebSocket for the agent inbox

**Decision.** New `POST /api/chat/stream` returns `text/event-stream` and
streams tokens. The existing `WS /api/chat/ws/{id}` stays for the dashboard.

**Why.**
- SSE is one-way (server → client), which is exactly what the chat widget
  needs while the bot is generating. It works through every proxy and CDN
  with `Cache-Control: no-cache` + `X-Accel-Buffering: no`. Easier to
  deploy than WebSockets.
- WebSockets stay because the agent dashboard needs *both* directions and
  multiple subscribers per conversation (multiple agent tabs watching the
  same chat).

**Trade-off.** Two streaming primitives. Acceptable because each fits its
use case naturally.

---

## ADR-007: Tool-using agent alongside the linear RAG pipeline

**Decision.** Keep the linear `AIEngine.process_message` (intent → RAG →
answer → confidence → handoff) **and** add a new `Agent` class that runs a
tool-use loop. Expose them as separate endpoints (`POST /api/chat`,
`POST /api/chat/agent`).

**Why.**
- The linear pipeline is fast (1 LLM call + 1 RAG query) and predictable
  — perfect for short FAQ-style questions, which are the majority.
- The agent shines on multi-step requests ("can someone call me about
  pricing tomorrow morning?") where the model needs to chain KB lookup +
  contact capture + escalation in one turn. Forcing every message through
  a 3-iteration agent loop would be wasteful and slow.
- Tools live in a registry (`tools.py`), so adding capabilities (calendar
  booking, order lookup, payment links) is a one-file change with no
  plumbing.

**Trade-off.** Two pipelines means two endpoints and two test paths. Worth
it because their performance and cost profiles are genuinely different.

---

## ADR-008: Pydantic-Settings + `@lru_cache` over a config module of constants

**Decision.** All config in `Settings(BaseSettings)`, accessed via
`get_settings()` cached singleton.

**Why.**
- Type-safe (`port: int = 8001` is validated on load).
- Single source of truth for env vars; the `.env.example` mirrors it
  one-to-one.
- `@lru_cache` makes `get_settings()` cheap to call from anywhere without
  passing a config object through every function.

**Trade-off.** None worth mentioning.
