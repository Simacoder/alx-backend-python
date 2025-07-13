import time
import sqlite3 
import functools

def with_db_connection(func):
    """
    Decorator that automatically handles database connections.
    
    This decorator opens a database connection, passes it to the decorated
    function as the first argument, and ensures the connection is properly
    closed afterward, even if an exception occurs.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Open database connection
        conn = sqlite3.connect('users.db')
        
        try:
            # Call the original function with connection as first argument
            result = func(conn, *args, **kwargs)
            return result
        finally:
            # Always close the connection
            conn.close()
    
    return wrapper

query_cache = {}

def cache_query(func):
    """
    Decorator that caches database query results based on the SQL query string.
    
    This decorator stores query results in a global cache dictionary using
    the SQL query string as the key. Subsequent calls with the same query
    will return the cached result instead of executing the query again.
    """
    @functools.wraps(func)
    def wrapper(conn, *args, **kwargs):
        # Extract the query from function arguments
        # Check if 'query' is in kwargs
        if 'query' in kwargs:
            query = kwargs['query']
        # If not in kwargs, assume it's the first positional argument after conn
        elif len(args) > 0:
            query = args[0]
        else:
            query = None
        
        # If we can't find a query, execute without caching
        if query is None:
            print("[CACHE] No query found, executing without caching")
            return func(conn, *args, **kwargs)
        
        # Normalize the query string for consistent caching
        normalized_query = ' '.join(query.strip().split())
        
        # Check if result is already cached
        if normalized_query in query_cache:
            print(f"[CACHE] Cache hit for query: {normalized_query}")
            return query_cache[normalized_query]
        
        # Cache miss - execute the query
        print(f"[CACHE] Cache miss for query: {normalized_query}")
        result = func(conn, *args, **kwargs)
        
        # Store the result in cache
        query_cache[normalized_query] = result
        print(f"[CACHE] Result cached for query: {normalized_query}")
        
        return result
    
    return wrapper

@with_db_connection
@cache_query
def fetch_users_with_cache(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

#### First call will cache the result
print("=== First call (should cache) ===")
users = fetch_users_with_cache(query="SELECT * FROM users")
print(f"Retrieved {len(users) if users else 0} users")

#### Second call will use the cached result
print("\n=== Second call (should use cache) ===")
users_again = fetch_users_with_cache(query="SELECT * FROM users")
print(f"Retrieved {len(users_again) if users_again else 0} users")

#### Display cache status
print(f"\n=== Cache Status ===")
print(f"Cache contains {len(query_cache)} entries")
for query in query_cache.keys():
    print(f"Cached query: {query}")