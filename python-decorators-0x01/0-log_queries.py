# Simple queries
import sqlite3
import functools

#### decorator to log SQL queries

def log_queries(func):
    """
    Decorator that logs SQL queries before executing them.
    
    This decorator intercepts function calls and logs the SQL query
    parameter passed to the function before execution.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract the query from function arguments
        # Check if 'query' is in kwargs
        if 'query' in kwargs:
            query = kwargs['query']
        # If not in kwargs, assume it's the first positional argument
        elif args:
            query = args[0]
        else:
            query = "No query found"
        
        # Log the SQL query
        print(f"[SQL LOG] Executing query: {query}")
        
        # Execute the original function
        result = func(*args, **kwargs)
        
        # for log completion
        print(f"[SQL LOG] Query completed successfully")
        
        return result
    
    return wrapper

@log_queries
def fetch_all_users(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

#### fetch users while logging the query
users = fetch_all_users(query="SELECT * FROM users")