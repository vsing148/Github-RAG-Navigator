from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import psycopg2
import os
from fastapi.middleware.cors import CORSMiddleware


from search_router import route_query, perform_hybrid_search
from ingest_github import fetch_closed_issues, insert_issues_to_db
from generate_embeddings import generate_embeddings

DB_URL = os.getenv("DATABASE_URL")

app = FastAPI(
    title="Dynamic Enterprise RAG API",
    description="Ingest any GitHub repo and search it using Vector + SQL filtering."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows any frontend to connect (good for local dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST SCHEMAS ---
class IngestRequest(BaseModel):
    repo_owner: str
    repo_name: str
    limit: int = 20 # Defaulting to 20 issues

class SearchRequest(BaseModel):
    repo_owner: str
    repo_name: str
    query: str

# --- ENDPOINTS ---
@app.get("/api/repos")
def get_repos():
    """Returns all repos currently ingested in the database, with issue counts."""
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT repo_name, COUNT(*) as issue_count
            FROM github_issues
            GROUP BY repo_name
            ORDER BY issue_count DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return {
            "repos": [
                {"repo_name": row[0], "issue_count": row[1]}
                for row in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
def ingest_repo(request: IngestRequest):
    """Fetches issues from GitHub, saves them to Postgres, and generates AI embeddings."""
    try:
        # Fetch from GitHub
        issues = fetch_closed_issues(request.repo_owner, request.repo_name, limit=request.limit)
        
        # Insert into Supabase
        inserted_count = insert_issues_to_db(issues, request.repo_owner, request.repo_name)
        
        # Embed the new issues immediately
        repo_full_name = f"{request.repo_owner}/{request.repo_name}"
        embedded_count = generate_embeddings(repo_full_name)
        
        return {
            "message": f"Successfully processed {repo_full_name}",
            "fetched_from_github": len(issues),
            "new_issues_inserted": inserted_count,
            "issues_embedded": embedded_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
def search_issues(request: SearchRequest):
    """Translates a natural language question into a vector search filtered by repo."""
    try:
        target_repo = f"{request.repo_owner}/{request.repo_name}"
        
        # Ask the AI to extract labels/intent
        extracted_filters = route_query(request.query)
        
        # Perform Hybrid Search locked to the specific repo
        search_results = perform_hybrid_search(extracted_filters, target_repo)
        
        return {
            "target_repo": target_repo,
            "original_query": request.query,
            "applied_filters": extracted_filters.labels,
            "semantic_search_string": extracted_filters.semantic_search,
            "results": search_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)