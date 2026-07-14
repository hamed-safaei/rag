# RAG Chat API

A production-ready backend for a **Retrieval-Augmented Generation (RAG) chat assistant**, built with **FastAPI**, **SQLAlchemy**, and a **LangGraph-based agent**. It handles authenticated chat sessions, persists conversation history, and routes user queries through a custom retrieval / conversation-history / answer-generation graph.

---

## ✨ Features

- 🔐 **JWT authentication** via HTTP-only cookies
- 💬 **Session-based chat** — start a new session automatically or continue an existing one
- 🧭 **Query routing** — an LLM-based router classifies every incoming query as `retrieve`, `history`, `both`, or `none` before any retrieval work happens
- 🧠 **RAG agent integration** — queries are routed through a LangGraph `GraphState` pipeline (parent/child chunk retrieval, rerank, evaluation + retry logic, and conversation-history lookup)
- 🔀 **Parallel branches with a synchronized join** — the retrieval branch and the conversation-history branch run as independent, always-scheduled graph branches (each a fast no-op when not needed) and are joined before generation, so `generate` always runs exactly once per request
- 🗂️ **Full conversation history** — retrieve all messages of a session, ordered chronologically, labeled by role (`user` / `agent`); the last 10 messages are also available to the agent itself for follow-up questions
- 🛡️ **Ownership enforcement** — a user can only access their own sessions and messages
- 🧩 **Clean layered architecture** — routers → dependencies → repositories → models, fully decoupled from the agent logic
- 🔁 **Shared DB session** — the agent reuses the request's SQLAlchemy session (injected via LangGraph's `config.configurable`) instead of opening a separate connection

---

## 🏗️ Architecture

```
Client
  │
  ▼
FastAPI Router (api/v1/routers)
  │
  ▼
Dependencies (auth, session ownership) ──► JWT validation, access control
  │
  ▼
Repositories (SQLAlchemy) ──► PostgreSQL (users, sessions, messages, tokens, feedbacks)
  │
  ▼
Agent (LangGraph) ──► Router → [Retrieval branch ‖ History branch] → Answer generation
```

---

## 🛠️ Tech Stack

| Layer               | Technology                          |
|----------------------|--------------------------------------|
| API framework         | FastAPI                             |
| ORM                    | SQLAlchemy                          |
| Database                | PostgreSQL (`uuid`, `jsonb` columns) |
| Auth                     | JWT (HTTP-only cookies)             |
| Validation                | Pydantic                            |
| Agent / RAG engine         | LangGraph (`TypedDict` state graph) |
| LLM orchestration            | LangChain (`ChatOpenAI`, structured output) |
| Observability                  | Langfuse (`@observe` on every node) |

---

## 📁 Project Structure

```
app/
├── agent/
│   ├── agent.py                 # run_agent(query, session_id, db) → GraphState pipeline
│   ├── graph.py                 # builds and compiles the LangGraph StateGraph
│   ├── nodes.py                 # route / retrieve / evaluate / transform / history / generate nodes
│   ├── prompts.py               # generator_prompt, evaluator_prompt, router_prompt, ...
│   ├── chians.py                # LLM instances + LCEL chains (generator_chain, router_chain, ...)
│   ├── schema/
│   │   └── graphstate.py        # GraphState TypedDict
│   └── services/
│       ├── generator.py         # generate_answer(query, context, history)
│       ├── evaluator.py         # evaluate_retrieved(...)
│       ├── transformer.py       # route_query(...) — sub-query decomposition for retries
│       └── router.py            # classify_query(...) — history/retrieve/both/none classifier
├── api/
│   └── v1/
│       ├── api.py               # aggregates all routers
│       ├── dependencies/
│       │   ├── authorized_jwt.py       # get_jwt_auth_user
│       │   └── authorized_session.py   # get_authorized_session
│       └── routers/
│           ├── auth.py
│           ├── session.py       # session CRUD + message history
│           └── chat.py          # send message / get agent reply
├── core/
│   └── database/
│       └── database.py          # get_app_db (DB session dependency)
├── models/
│   ├── database/
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── tokens.py
│   │   └── feedbacks.py
│   └── schemas/
│       ├── user.py
│       ├── session.py
│       └── message.py           # ChatRequest, ChatResponse, MessageItem
└── repositories/
    ├── user_repository.py
    ├── session_repository.py
    ├── message_repository.py
    └── token_repository.py
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- [Poetry](https://python-poetry.org/) or `pip` for dependency management

### Installation

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# Auth
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Agent / RAG
OPENAI_API_KEY=your-gapgpt-or-openai-key
```

### Database Migrations

```bash
alembic upgrade head
```

### Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

---

## 📡 API Reference

### Auth

| Method | Endpoint          | Description                     |
|--------|--------------------|----------------------------------|
| POST   | `/auth/login`       | Authenticate and set access token cookie |
| POST   | `/auth/logout`      | Clear access token cookie        |

### Sessions

| Method | Endpoint                        | Description                                              |
|--------|-----------------------------------|------------------------------------------------------------|
| GET    | `/sessions`                        | List all sessions of the current user                     |
| GET    | `/sessions/{session_id}/messages`  | Get full conversation history of a session, ordered chronologically |

**Response example** — `GET /sessions/{session_id}/messages`
```json
[
  { "role": "user",  "content": "What is RAG?" },
  { "role": "agent", "content": "RAG stands for Retrieval-Augmented Generation..." },
  { "role": "user",  "content": "Give me an example." },
  { "role": "agent", "content": "Sure — imagine a chatbot that..." }
]
```

### Chat

| Method | Endpoint      | Description                                                        |
|--------|----------------|----------------------------------------------------------------------|
| POST   | `/chat/send`    | Send a message. Creates a new session if `session_id` is `null`, otherwise appends to the existing session |

**Request body**
```json
{
  "session_id": null,
  "content": "What is retrieval-augmented generation?"
}
```

**Response**
```json
{
  "session_id": "b3f1c2a4-1234-4a5b-9c6d-abcdef123456",
  "answer": "Retrieval-Augmented Generation combines...",
  "user_message": { "id": 1, "role": "user", "content": "...", "created_at": "..." },
  "assistant_message": { "id": 2, "role": "agent", "content": "...", "created_at": "..." }
}
```

All endpoints (except auth) require a valid `access_token` cookie and enforce that the requesting user owns the target session (`403 Forbidden` otherwise, `404 Not Found` if the session doesn't exist).

---

## 🧠 The Agent

### Overview

`run_agent(query: str, session_id: str, db: Session)` executes a LangGraph pipeline. The current user's SQLAlchemy session (`db`) is injected into the graph via LangGraph's `config.configurable`, so the agent reuses the same DB connection/transaction as the rest of the request instead of opening a new one.

### State

```python
class GraphState(TypedDict, total=False):
    # input
    query: str
    session_id: str

    # router output
    route: str  # "history" | "retrieve" | "both" | "none"

    # retrieval branch
    parent_ids: List[str]
    child_ids: List[str]
    context: str
    retried: bool

    # history branch
    history: List[Dict[str, str]]

    # final output
    answer: str

    # internal / helper fields
    child_records: List[Dict[str, Any]]
    child_after_transform: List[Dict[str, Any]]
    needs_retry: bool
```

### Pipeline

```
                 ┌─────────┐
                 │  route  │  ← LLM classifier: history / retrieve / both / none
                 └────┬────┘
           ┌──────────┴──────────┐
           ▼                     ▼
     ┌───────────┐         ┌───────────┐
     │  retrieve │         │  history  │
     └─────┬─────┘         └─────┬─────┘
           ▼                     │
     ┌───────────┐               │
     │  evaluate │◄──┐           │
     └─────┬─────┘   │           │
           │needs_retry           │
           ▼          │           │
     ┌───────────┐    │           │
     │ transform │────┘           │
     └─────┬─────┘                │
           ▼                      │
   ┌────────────────┐             │
   │  retrieve_done  │            │
   └────────┬────────┘            │
            └──────────┬──────────┘
                        ▼
                  ┌───────────┐
                  │ generate  │
                  └───────────┘
```

1. **`route`** — an LLM router (`app/agent/services/router.py`) classifies the query into exactly one of `history`, `retrieve`, `both`, `none`.
2. **`retrieve` / `history` branches always run** (LangGraph fan-out), but each is a fast no-op internally when the router decision doesn't require it (e.g. `node_retrieve` skips the vector search entirely when `route == "history"`). This keeps the graph's join deterministic and deadlock-free without adding real cost — a skipped branch is just an `if` check, not an extra LLM/DB call.
3. **Retrieval branch**: `retrieve` (vector search + rerank) → `evaluate` (LLM checks if the retrieved chunks answer the query, may trigger one `transform` retry with decomposed sub-queries) → `retrieve_done`.
4. **History branch**: `history` fetches the last 10 messages of the session directly with the shared `db` session.
5. **Join**: `generate` only fires once both `retrieve_done` and `history` have completed (`workflow.add_edge(["retrieve_done", "history"], "generate")`), regardless of which branch took longer.
6. **`generate`** — combines `context` (from retrieval) and `history` (from conversation) into the final answer. For `route == "none"`, a fixed out-of-scope message is returned without calling the LLM at all.

### Why not route directly from `route` to `generate` for `none`?

A direct conditional edge alongside the join-based edge would give `generate` two independent trigger paths, causing it to run twice per request (once immediately, once when the join resolves). Keeping a single, always-taken path through the no-op branches avoids this race condition entirely — see `app/agent/nodes.py` for the guards (`_needs_retrieve`, `_needs_history`).

---

## 🗄️ Database Schema (core tables)

**sessions**
| Column      | Type      |
|-------------|-----------|
| id          | uuid      |
| user_id     | integer   |
| title       | varchar   |
| created_at  | timestamp |

**messages**
| Column          | Type      |
|-----------------|-----------|
| id              | integer   |
| session_id      | uuid      |
| role            | varchar   |
| content         | text      |
| agent_metadata  | jsonb     |
| created_at      | timestamp |

---

## 🧪 Testing

```bash
pytest
```

Suggested manual smoke tests for the agent (see `app/agent/agent.py`):

| Query example                                              | Expected `route` |
|--------------------------------------------------------------|-------------------|
| "تفاوت RAG با fine-tuning چیه؟"                              | `retrieve`        |
| "سوال قبلی من چی بود؟"                                        | `history`         |
| "همون روشی که گفتی رو با جزئیات بیشتر توضیح بده"                | `both`            |
| "امروز هوا چطوره؟"                                            | `none`            |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch and open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).