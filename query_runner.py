import pandas as pd
from db_setup import get_engine

def load_queries(filepath='queries.sql'):
    with open(filepath, 'r') as f:
        content = f.read()
        
    queries = {}
    current_name = None
    current_query = []
    
    for line in content.split('\n'):
        if line.startswith('-- @name:'):
            if current_name and current_query:
                queries[current_name] = '\n'.join(current_query).strip()
            current_name = line.replace('-- @name:', '').strip()
            current_query = []
        elif not line.startswith('--') or line.startswith('-- @name:') == False:
            # We can keep normal comments in the SQL or strip them, but keeping them is fine.
            # However, it's safer to just skip full-line comments to avoid issues, or keep them if they are part of the query block.
            if not line.startswith('--'):
                current_query.append(line)
            
    if current_name and current_query:
        queries[current_name] = '\n'.join(current_query).strip()
        
    return queries

# Load queries on import
QUERIES = load_queries()

def run_query(query_name, engine=None):
    """
    Executes a named SQL query against the SQLite database and returns a Pandas DataFrame.
    """
    if engine is None:
        engine = get_engine()
        
    if query_name not in QUERIES:
        raise ValueError(f"Query '{query_name}' not found in queries.sql")
        
    query = QUERIES[query_name]
    return pd.read_sql_query(query, engine)

if __name__ == "__main__":
    print(f"Loaded {len(QUERIES)} queries from queries.sql:")
    for q in QUERIES:
        print(f" - {q}")
