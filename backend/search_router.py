import os
import psycopg2
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from openai import OpenAI

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DB_URL:
    raise ValueError("DATABASE_URL is missing!")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing! Please add it to your .env file.")

# Initialize our standard OpenAI client (for embeddings) and our LangChain Chat Model (for routing)
embed_client = OpenAI(api_key=OPENAI_API_KEY)

# 4o mini is fast, cheap, and great at extracting JSON
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0) # Temp 0 means the llm will be deterministic and consistent

# Define output structure (JSON Schema)
class QueryFilters(BaseModel):

    # List of strings that the LLM will extract from the user's query
    labels: list[str] = Field(
        default_factory=list, 
        description="List of issue labels to filter by (e.g. 'bug', 'documentation', 'enhancement'). Leave empty if not specified."
    )

    # The core subject of the user's search to be used for semantic similarity search. 
    semantic_search: str = Field(
        description="The core subject of the user's search to be used for semantic similarity search. Remove any mentions of labels from this string."
    )


# Passes the user query to the LLM to extract structured filters.
def route_query(user_query: str) -> QueryFilters: 
    print(f"\n Routing query: '{user_query}'")

    # LangChain's 'with_structured_output' forces the LLM to return our Pydantic model
    structured_llm = llm.with_structured_output(QueryFilters) 

    result = structured_llm.invoke(user_query)

    print(f"Extracted Labels: {result.labels}")
    print(f"Extracted Search: '{result.semantic_search}'")
    return result

def perform_hybrid_search(filters: QueryFilters, target_repo: str):
    # Embeds the search string and queries the database using Vector + SQL

    print(f"Generating vector for the search string inside repo: {target_repo}...")

    # Convert the semantic search string into a vector that OpenAI can understand (1536 floats)
    response = embed_client.embeddings.create(
        input=filters.semantic_search,
        model="text-embedding-3-small"
    )
    search_vector = response.data[0].embedding

    print("Executing Hybrid Vector + SQL Search in Supabase...")
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    # SQL query
    # <=> is the cosine distance operator in pgvector, lower distance means it is more semantically similar.
    sql_query = """
        SELECT issue_number, title, labels, (embedding <=> %s::vector) AS distance
        FROM github_issues
        WHERE repo_name = %s
    """

    params = [search_vector, target_repo] # Search vector is passed as a parameter to the SQL query

    # Add SQL Metadata Filtering dynamically if the LLM found labels
    if filters.labels:
        # PostgreSQL syntax to check if arrays overlap: labels && ARRAY['bug']
        sql_query += " AND labels && %s::text[]"
        params.append(filters.labels)

    sql_query += " ORDER BY distance ASC LIMIT 3" # Limit to top 3 results

    
    cursor.execute(sql_query, tuple(params)) # Execute the SQL query, we convert list of params into a tuple
    results = cursor.fetchall()

    formatted_results = []

    print("\nSEARCH RESULTS")
    if not results:
        print("No matches found.")
    else:
        for idx, row in enumerate(results):
            issue_num, title, labels, distance = row
            similarity = (1 - (distance / 2)) * 100 
            
            print(f"{idx + 1}. Issue #{issue_num}: {title}")
            print(f"   Labels: {labels}")
            print(f"   Match Score: {similarity:.1f}%")
            print("   ---------------------------------------------")
            
            # Save the result into a clean dictionary
            formatted_results.append({
                "issue_number": issue_num,
                "title": title,
                "labels": labels,
                "match_score": round(similarity, 1)
            })

    cursor.close()
    conn.close()

    return formatted_results


if __name__ == "__main__":
    test_question = "Find some bugs related to authentication or login issues"
    test_repo = "langchain-ai/langchain"
    extracted_filters = route_query(test_question)
    perform_hybrid_search(extracted_filters, test_repo)