import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Safety checks
if not DB_URL:
    raise ValueError("DATABASE_URL is missing!")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing! Please add it to your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_embeddings(repo_full_name: str = None):
    # Finds unembedded issues for a specific repo and embeds them.
    print(f"Connecting to database to embed new issues for {repo_full_name or 'all repos'}...") # if repo_full_name is None, it will embed all issues
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    # Query conditionally based on whether a repo was provided
    query = "SELECT id, title, body FROM github_issues WHERE embedding IS NULL"
    params = []
    
    if repo_full_name:
        query += " AND repo_name = %s"
        params.append(repo_full_name)
    
    # Execute the query
    # tuple(params) converts the list of parameters into a tuple
    cursor.execute(query, tuple(params))
    issues = cursor.fetchall()
    
    if not issues:
        print("No new issues to embed.")
        return 0


    count = 0
    # Iterate through the issues and generate embeddings
    for issue in issues:
        issue_id, title, body = issue
        combined_text = f"Title: {title}\n\nDescription: {body or ''}"
        
        # Added a try-except block to handle potential errors during embedding generation
        try:
            response = client.embeddings.create(
                input=combined_text,
                model="text-embedding-3-small"
            )
            embedding_vector = response.data[0].embedding 
            
            # Update the database with the embedding vector
            cursor.execute("""
                UPDATE github_issues 
                SET embedding = %s 
                WHERE id = %s
            """, (embedding_vector, issue_id))
            
            count += 1
  
        except Exception as e:
            print(f"Failed to embed issue {issue_id}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\nSuccessfully generated and saved {count} embeddings!")
    return count

if __name__ == "__main__":
    generate_embeddings()