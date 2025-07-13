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
            # Commit any pending transactions
            conn.commit()
            return result
        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            raise e
        finally:
            # Always close the connection
            conn.close()
    
    return wrapper

@with_db_connection 
def get_user_by_id(conn, user_id): 
    cursor = conn.cursor() 
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)) 
    return cursor.fetchone() 

#### Fetch user by ID with automatic connection handling 
user = get_user_by_id(user_id=1)
print(user)