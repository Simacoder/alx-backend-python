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

def transactional(func):
    """
    Decorator that manages database transactions.
    
    This decorator ensures that the decorated function runs within a transaction.
    If the function completes successfully, the transaction is committed.
    If an exception occurs, the transaction is rolled back.
    """
    @functools.wraps(func)
    def wrapper(conn, *args, **kwargs):
        try:
            # Begin transaction (SQLite auto-begins transactions)
            result = func(conn, *args, **kwargs)
            # Commit the transaction if successful
            conn.commit()
            return result
        except Exception as e:
            # Rollback the transaction if an error occurs
            conn.rollback()
            # Re-raise the exception to allow proper error handling
            raise e
    
    return wrapper

@with_db_connection 
@transactional 
def update_user_email(conn, user_id, new_email): 
    cursor = conn.cursor() 
    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id)) 

#### Update user's email with automatic transaction handling 
update_user_email(user_id=1, new_email='Crawford_Cartwright@hotmail.com')