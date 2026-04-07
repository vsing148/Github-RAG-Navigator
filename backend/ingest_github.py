import os
import requests
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Safety check
if not DB_URL:
    raise ValueError(
        "DATABASE_URL is missing! Python cannot find it. "
        "Please ensure your file is named exactly '.env', is saved in the 'backend' folder, "
        "and contains DATABASE_URL=\"your_supabase_url\""
    )


def fetch_closed_issues(repo_owner: str, repo_name: str, limit: int = 20):
    # Fetches up to 20 closed issues from a dynamic GitHub repository.
    print(f"Fetching {limit} issues from {repo_owner}/{repo_name}...")
    
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    headers = {"Accept": "application/vnd.github+json"}
    
    # Headers to authenticate with github
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    
    # We only want actual closed bugs/issues, not open ones
    params = {
        "state": "closed",
        "per_page": limit, 
        "page": 1
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    # Give a clear error if the user types a repo that doesn't exist
    if response.status_code == 404:
        raise ValueError(f"Repository {repo_owner}/{repo_name} not found or is private.")
        
    response.raise_for_status()
    
    issues = response.json()
    actual_issues = [i for i in issues if "pull_request" not in i]
    print(f"Retrieved {len(actual_issues)} actual issues.")
    
    return actual_issues

def insert_issues_to_db(issues, repo_owner: str, repo_name: str):
    # Inserts the dynamically fetched issues into Supabase.
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO github_issues (
            id, repo_name, issue_number, title, body, state, created_at, closed_at, labels
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """
    
    count = 0
    repo_full_name = f"{repo_owner}/{repo_name}" # e.g., "langchain-ai/langchain"
    
    for issue in issues:
        label_names = [label["name"] for label in issue.get("labels", [])]
        
        cursor.execute(insert_query, (
            issue["id"],
            repo_full_name,
            issue["number"],
            issue["title"],
            issue.get("body", ""), 
            issue["state"],
            issue["created_at"],
            issue["closed_at"],
            label_names
        ))
        count += cursor.rowcount # rowcount will be 0 if the issue already existed
        
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Successfully inserted {count} new issues into the database.")
    return count