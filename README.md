# IssueRAG — Semantic GitHub Issue Search
 
> Built with **Python 3.11** · **Supabase** · **PostgreSQL** · **FastAPI** · **React** · **Vite** · **LangChain** · **OpenAI**
 
---
 
IssueRAG is a full-stack RAG (Retrieval-Augmented Generation) application that lets you ingest any public GitHub repository and search its closed issues using natural language. Instead of keyword matching, it uses vector embeddings and an LLM-powered query router to understand the *intent* behind your search — returning the most semantically relevant issues with match scores, label filters, and direct links to GitHub.
 
---
 
## Features
 
- **Natural language search** — Ask questions like *"find authentication bugs"* or *"issues with memory leaks in the renderer"* instead of guessing exact keywords
- **Hybrid search** — Combines pgvector cosine similarity with SQL metadata filtering for precision results
- **LLM query routing** — GPT-4o-mini automatically extracts label filters and semantic intent from your query before searching
- **Multi-repo support** — Ingest as many repositories as you want; all data is namespaced per repo so searches never bleed across projects
- **Live embedding pipeline** — Issues are embedded with `text-embedding-3-small` immediately after ingestion, no manual step required
- **GitHub-themed UI** — Dark mode React frontend with real-time toasts, match score bars, label badges, and clickable issue links
 
---
 
## Architecture
 
```
┌─────────────────────────────────────────────────────────┐
│                     React + Vite Frontend                │
│         Ingest Panel · Repo Selector · Search UI         │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (FastAPI)
┌───────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  POST /api/ingest          POST /api/search              │
│  ┌─────────────────┐       ┌──────────────────────────┐  │
│  │ 1. GitHub API   │       │ 1. LangChain + GPT-4o-   │  │
│  │    fetch issues │       │    mini → extract labels  │  │
│  │ 2. Insert to DB │       │    + semantic string      │  │
│  │ 3. OpenAI embed │       │ 2. OpenAI embed query     │  │
│  └─────────────────┘       │ 3. pgvector cosine search │  │
│                            │    + SQL label filtering  │  │
│  GET /api/repos            └──────────────────────────┘  │
│  └─ List all indexed repos with issue counts             │
└───────────────────────┬─────────────────────────────────┘
                        │ psycopg2
┌───────────────────────▼─────────────────────────────────┐
│              Supabase (PostgreSQL + pgvector)             │
│                                                          │
│  github_issues table                                     │
│  ┌──────────────┬──────────────┬───────────────────────┐ │
│  │ id           │ repo_name    │ issue_number          │ │
│  │ title        │ body         │ labels (text[])       │ │
│  │ state        │ created_at   │ closed_at             │ │
│  │ embedding    │ (vector 1536 dimensions)             │ │
│  └──────────────┴──────────────┴───────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```
 
---
 
## Tech Stack
 
| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Backend framework | FastAPI |
| Database | Supabase (PostgreSQL) |
| Vector search | pgvector |
| ORM / DB driver | psycopg2 |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM query routing | LangChain + GPT-4o-mini |
| Frontend | React + Vite |
| Data validation | Pydantic |
| GitHub data | GitHub REST API |
 
---
 
## Project Structure
 
```
issuerag/
├── backend/
│   ├── main.py                 # FastAPI app, CORS, endpoint definitions
│   ├── search_router.py        # LangChain query router + hybrid search logic
│   ├── generate_embeddings.py  # OpenAI embedding pipeline
│   ├── ingest_github.py        # GitHub API fetching + Supabase insertion
│   └── .env                    # Environment variables (not committed)
│
├── frontend/
│   ├── src/
│   │   └── App.jsx             # Full React UI
│   ├── index.html
│   └── vite.config.js
│
└── README.md
```
 
---
 
## Getting Started
 
### Prerequisites
 
- Python 3.11
- Node.js 18+
- A [Supabase](https://supabase.com) project with the `pgvector` extension enabled
- An [OpenAI](https://platform.openai.com) API key
- A [GitHub](https://github.com/settings/tokens) personal access token (optional, increases rate limits)
 
### 1. Supabase Setup
 
In your Supabase SQL editor, run the following to enable pgvector and create the issues table:
 
```sql
-- Enable the pgvector extension
create extension if not exists vector;
 
-- Create the issues table
create table github_issues (
  id bigint primary key,
  repo_name text not null,
  issue_number integer not null,
  title text,
  body text,
  state text,
  created_at timestamptz,
  closed_at timestamptz,
  labels text[],
  embedding vector(1536)
);
 
-- Index for fast repo filtering
create index idx_repo_name on github_issues (repo_name);
 
-- Index for fast vector search
create index on github_issues using ivfflat (embedding vector_cosine_ops);
```
 
### 2. Backend Setup
 
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn psycopg2-binary openai langchain langchain-openai python-dotenv requests pydantic
```
 
Create a `.env` file in the `backend/` directory:
 
```env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
```
 
Start the server:
 
```bash
uvicorn main:app --reload
```
 
The API will be live at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.
 
### 3. Frontend Setup
 
```bash
cd frontend
npm install
npm run dev
```
 
The app will be live at `http://localhost:5173`.
 
---
 
## API Reference
 
### `GET /api/repos`
Returns all repositories currently indexed in the database.
 
```json
{
  "repos": [
    { "repo_name": "langchain-ai/langchain", "issue_count": 20 },
    { "repo_name": "facebook/react", "issue_count": 15 }
  ]
}
```
 
### `POST /api/ingest`
Fetches closed issues from a GitHub repository, stores them in Supabase, and generates embeddings.
 
```json
{
  "repo_owner": "facebook",
  "repo_name": "react",
  "limit": 20
}
```
 
**Response:**
```json
{
  "message": "Successfully processed facebook/react",
  "fetched_from_github": 20,
  "new_issues_inserted": 18,
  "issues_embedded": 18
}
```
 
### `POST /api/search`
Searches a repository's issues using natural language. The LLM automatically extracts label filters and semantic intent before querying.
 
```json
{
  "repo_owner": "facebook",
  "repo_name": "react",
  "query": "find bugs related to concurrent rendering"
}
```
 
**Response:**
```json
{
  "target_repo": "facebook/react",
  "original_query": "find bugs related to concurrent rendering",
  "applied_filters": ["bug"],
  "semantic_search_string": "concurrent rendering issues",
  "results": [
    {
      "issue_number": 24671,
      "title": "Concurrent mode causes flicker on state updates",
      "labels": ["bug", "React Core"],
      "match_score": 91.4
    }
  ]
}
```
 
---
 
## How the Search Works
 
1. **Query routing** — Your natural language query is passed to GPT-4o-mini via LangChain's `with_structured_output`. The model extracts two things: any label filters mentioned (e.g. `bug`, `documentation`) and a clean semantic search string stripped of filter language.
 
2. **Embedding** — The semantic search string is embedded into a 1536-dimensional vector using OpenAI's `text-embedding-3-small`.
 
3. **Hybrid search** — pgvector computes cosine distance (`<=>`) between the query vector and every issue embedding in the target repo. If the LLM extracted label filters, a SQL `&&` array overlap check is applied simultaneously, narrowing results to only issues that carry those labels.
 
4. **Ranking** — The top 3 results are returned, ordered by cosine similarity. Match scores are computed as `(1 - distance/2) * 100` and displayed as a percentage.
 
---
 
## Environment Variables
 
| Variable | Description |
|---|---|
| `DATABASE_URL` | Full Supabase PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM routing |
| `GITHUB_TOKEN` | GitHub personal access token (optional but recommended) |
 
---
 
## Deployment Notes
 
- When deploying the frontend, update the `API` base URL in `App.jsx` from `http://localhost:8000` to your backend's deployed URL.
- When deploying the backend, add your frontend's deployed origin to the `allow_origins` list in the CORS middleware in `main.py`.
- Ensure `pgvector` is enabled in your Supabase project before running any ingestion.
 
---
 
## License
 
MIT
