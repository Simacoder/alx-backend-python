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

def retry_on_failure(retries=3, delay=2):
    """
    Decorator that retries a function if it fails due to exceptions.
    
    Args:
        retries (int): Maximum number of retry attempts (default: 3)
        delay (int): Delay in seconds between retry attempts (default: 2)
    
    Returns:
        Decorator function that wraps the original function with retry logic
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            # Try the function execution up to (retries + 1) times
            for attempt in range(retries + 1):
                try:
                    # Attempt to execute the function
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    
                    # If this is the last attempt, don't retry
                    if attempt == retries:
                        print(f"[RETRY] Function '{func.__name__}' failed after {retries + 1} attempts")
                        raise last_exception
                    
                    # Log the retry attempt
                    print(f"[RETRY] Attempt {attempt + 1} failed for '{func.__name__}': {str(e)}")
                    print(f"[RETRY] Retrying in {delay} seconds... ({retries - attempt} attempts remaining)")
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

@with_db_connection
@retry_on_failure(retries=3, delay=1)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

#### attempt to fetch users with automatic retry on failure
users = fetch_users_with_retry()
print(users)