import sqlite3

class ExecuteQuery:
    """
    Reusable context manager that handles both database connection and query execution.
    
    This context manager takes a query and parameters, manages the database connection,
    executes the query, and returns the results automatically.
    """
    
    def __init__(self, query, params=None, database_path='users.db', fetch_method='fetchall'):
        """
        Initialize the ExecuteQuery context manager.
        
        Args:
            query (str): The SQL query to execute
            params (tuple/list): Parameters for the query (optional)
            database_path (str): Path to the SQLite database file
            fetch_method (str): Method to fetch results ('fetchall', 'fetchone', 'fetchmany')
        """
        self.query = query
        self.params = params or ()
        self.database_path = database_path
        self.fetch_method = fetch_method
        self.connection = None
        self.cursor = None
        self.results = None
    
    def __enter__(self):
        """
        Enter the context manager - open connection and execute query.
        
        Returns:
            query results: The results of the executed query
        """
        print(f"[QUERY] Opening connection to {self.database_path}")
        
        try:
            # Open database connection
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            
            # Create cursor
            self.cursor = self.connection.cursor()
            
            print(f"[QUERY] Executing query: {self.query}")
            if self.params:
                print(f"[QUERY] With parameters: {self.params}")
            
            # Execute the query with parameters
            if self.params:
                self.cursor.execute(self.query, self.params)
            else:
                self.cursor.execute(self.query)
            
            # Fetch results based on specified method
            if self.fetch_method == 'fetchall':
                self.results = self.cursor.fetchall()
            elif self.fetch_method == 'fetchone':
                self.results = self.cursor.fetchone()
            elif self.fetch_method == 'fetchmany':
                self.results = self.cursor.fetchmany()
            else:
                self.results = self.cursor.fetchall()
            
            print(f"[QUERY] Query executed successfully")
            if isinstance(self.results, list):
                print(f"[QUERY] Retrieved {len(self.results)} rows")
            elif self.results:
                print(f"[QUERY] Retrieved 1 row")
            else:
                print(f"[QUERY] No results found")
            
            return self.results
            
        except sqlite3.Error as e:
            print(f"[QUERY] Database error: {e}")
            self.results = None
            raise
        except Exception as e:
            print(f"[QUERY] Unexpected error: {e}")
            self.results = None
            raise
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager - handle cleanup and connection closing.
        
        Args:
            exc_type: Exception type (if any)
            exc_value: Exception value (if any)
            traceback: Exception traceback (if any)
            
        Returns:
            bool: False to propagate exceptions
        """
        if self.connection:
            try:
                if exc_type is None:
                    # No exception occurred, commit transaction
                    self.connection.commit()
                    print(f"[QUERY] Transaction committed successfully")
                else:
                    # Exception occurred, rollback transaction
                    self.connection.rollback()
                    print(f"[QUERY] Transaction rolled back due to exception: {exc_value}")
                
                # Close cursor if it exists
                if self.cursor:
                    self.cursor.close()
                
                # Close connection
                self.connection.close()
                print(f"[QUERY] Connection closed")
                
            except sqlite3.Error as e:
                print(f"[QUERY] Error during cleanup: {e}")
        
        # Return False to propagate any exceptions
        return False


# Test usage functions
def fetch_users_by_age():
    """
    Fetch users older than 25 using the ExecuteQuery context manager.
    """
    print("=== Fetching users older than 25 ===")
    
    try:
        with ExecuteQuery("SELECT * FROM users WHERE age > ?", (25,)) as results:
            if results:
                print(f"\nFound {len(results)} users older than 25:")
                for user in results:
                    print(f"  - {dict(user)}")
            else:
                print("No users found older than 25")
            return results
            
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []


def fetch_single_user():
    """
    Fetch a single user using fetchone method.
    """
    print("\n=== Fetching single user ===")
    
    try:
        with ExecuteQuery("SELECT * FROM users WHERE age > ? LIMIT 1", (25,), fetch_method='fetchone') as result:
            if result:
                print(f"Found user: {dict(result)}")
            else:
                print("No user found")
            return result
            
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


def fetch_all_users():
    """
    Fetch all users from the database.
    """
    print("\n=== Fetching all users ===")
    
    try:
        with ExecuteQuery("SELECT * FROM users") as results:
            if results:
                print(f"Found {len(results)} total users:")
                for user in results:
                    print(f"  - ID: {user['id']}, Name: {user.get('name', 'N/A')}, Age: {user.get('age', 'N/A')}")
            else:
                print("No users found in database")
            return results
            
    except Exception as e:
        print(f"Error fetching all users: {e}")
        return []


def demonstrate_error_handling():
    """
    Demonstrate error handling with invalid query.
    """
    print("\n=== Demonstrating error handling ===")
    
    try:
        with ExecuteQuery("SELECT * FROM non_existent_table") as results:
            print(f"This shouldn't print: {results}")
            
    except sqlite3.OperationalError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error: {e}")


# Main execution
if __name__ == "__main__":
    print("=== Reusable Query Context Manager Demo ===")
    
    # Main requirement: Execute the specified query
    print("\n" + "="*50)
    print("MAIN REQUIREMENT: SELECT * FROM users WHERE age > ? with parameter 25")
    print("="*50)
    
    users_over_25 = fetch_users_by_age()
    
    # Additional demonstrations
    single_user = fetch_single_user()
    all_users = fetch_all_users()
    demonstrate_error_handling()
    
    print(f"\n=== Summary ===")
    print(f"Users over 25: {len(users_over_25) if users_over_25 else 0}")
    print(f"Total users: {len(all_users) if all_users else 0}")
    
    print(f"\n=== Context Manager Features ===")
    print(" Automatic connection management")
    print(" Query execution with parameters")
    print(" Flexible fetch methods (fetchall, fetchone, fetchmany)")
    print(" Transaction management (commit/rollback)")
    print(" Proper resource cleanup")
    print(" Comprehensive error handling")
    print(" Reusable for any SQL query")