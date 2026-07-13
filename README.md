# RAG Chat API

A production-ready backend for a **Retrieval-Augmented Generation (RAG) chat assistant**, built with **FastAPI**, **SQLAlchemy**, and a **LangGraph-based agent**. It handles authenticated chat sessions, persists conversation history, and routes user queries through a custom retrieval/answer-generation graph.



## ✨ Features

- 🔐 **JWT authentication** via HTTP-only cookies
- 💬 **Session-based chat** — start a new session automatically or continue an existing one
- 🧠 **RAG agent integration** — queries are routed through a LangGraph `GraphState` pipeline (parent/child chunk retrieval + retry logic)
- 🗂️ **Full conversation history** — retrieve all messages of a session, ordered chronologically, labeled by role (`user` / `agent`)
- 🛡️ **Ownership enforcement** — a user can only access their own sessions and messages
- 🧩 **Clean layered architecture** — routers → dependencies → repositories → models, fully decoupled from the agent logic

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
Agent (LangGraph) ──► Retrieval (parent/child chunks) → Answer generation
```

---

## 🛠️ Tech Stack

| Layer            | Technology                          |
|-------------------|--------------------------------------|
| API framework      | FastAPI                             |
| ORM                | SQLAlchemy                          |
| Database           | PostgreSQL (`uuid`, `jsonb` columns) |
| Auth                | JWT (HTTP-only cookies)             |
| Validation          | Pydantic                            |
| Agent / RAG engine  | LangGraph (`TypedDict` state graph) |

---

## 📁 Project Structure

```
app/
├── agent/
│   └── agent.py                 # run_agent(query) → GraphState pipeline
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
# (add any keys your retrieval/LLM provider requires, e.g. OPENAI_API_KEY)
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

`run_agent(query: str)` executes a LangGraph pipeline defined by the following state:

```python
class GraphState(TypedDict):
    query: str
    parent_ids: List[str]
    child_ids: List[str]
    context: str
    retried: bool
    answer: str
```

The graph retrieves relevant parent/child document chunks, builds context, and — with an automatic retry step if the first attempt is insufficient — produces the final `answer` returned to the client.

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

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch and open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).