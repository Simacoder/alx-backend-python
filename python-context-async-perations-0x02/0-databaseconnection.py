import sqlite3

class DatabaseConnection:
    """
    Custom class-based context manager for database connections.
    
    This context manager automatically handles opening and closing database
    connections, ensuring proper resource management and cleanup.
    """
    
    def __init__(self, database_path='users.db'):
        """
        Initialize the context manager with a database path.
        
        Args:
            database_path (str): Path to the SQLite database file
        """
        self.database_path = database_path
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        """
        Enter the context manager - open database connection.
        
        Returns:
            sqlite3.Connection: The database connection object
        """
        print(f"[DB] Opening connection to {self.database_path}")
        
        try:
            # Open the database connection
            self.connection = sqlite3.connect(self.database_path)
            
            # Optional: Configure connection settings
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            
            print(f"[DB] Connection established successfully")
            return self.connection
            
        except sqlite3.Error as e:
            print(f"[DB] Error opening connection: {e}")
            raise
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager - close database connection.
        
        Args:
            exc_type: Exception type (if any)
            exc_value: Exception value (if any)
            traceback: Exception traceback (if any)
            
        Returns:
            bool: False to propagate exceptions (default behavior)
        """
        if self.connection:
            try:
                if exc_type is None:
                    # No exception occurred, commit any pending transactions
                    self.connection.commit()
                    print(f"[DB] Transaction committed successfully")
                else:
                    # Exception occurred, rollback any pending transactions
                    self.connection.rollback()
                    print(f"[DB] Transaction rolled back due to exception: {exc_value}")
                
                # Close the connection
                self.connection.close()
                print(f"[DB] Connection closed")
                
            except sqlite3.Error as e:
                print(f"[DB] Error during cleanup: {e}")
        
        # Return False to propagate any exceptions that occurred
        return False


# Example usage with the context manager
def fetch_all_users():
    """
    Fetch all users from the database using the custom context manager.
    """
    print("=== Fetching all users using context manager ===")
    
    try:
        # Use the context manager with the 'with' statement
        with DatabaseConnection('users.db') as conn:
            # Create cursor and execute query
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            
            # Fetch all results
            users = cursor.fetchall()
            
            print(f"[QUERY] Found {len(users)} users in the database")
            return users
            
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return []


# Test usage with error handling
def fetch_users_with_error_handling():
    """
    Demonstrate error handling with the context manager.
    """
    print("\n=== Demonstrating error handling ===")
    
    try:
        with DatabaseConnection('users.db') as conn:
            cursor = conn.cursor()
            
            # This might fail if the table doesn't exist
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            
            # Print results
            if users:
                print("\nUsers found:")
                for user in users:
                    # Since we set row_factory to sqlite3.Row, we can access columns by name
                    print(f"  User: {dict(user)}")
            else:
                print("No users found in the database")
                
            return users
            
    except sqlite3.OperationalError as e:
        print(f"[ERROR] Table or database issue: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return []


# Main execution
if __name__ == "__main__":
    print("=== Custom Database Context Manager Demo ===")
    
    # Basic usage
    users = fetch_all_users()
    
    # Usage with enhanced error handling
    users_with_handling = fetch_users_with_error_handling()
    
    print(f"\n=== Summary ===")
    print(f"Total users retrieved: {len(users)}")
    
    # Test of what the context manager handles automatically:
    print("\n=== What the context manager handles ===")
    print(" Opening database connection")
    print(" Configuring connection settings")
    print(" Committing transactions on success")
    print(" Rolling back transactions on errors")
    print(" Closing connection automatically")
    print(" Proper exception handling and cleanup")