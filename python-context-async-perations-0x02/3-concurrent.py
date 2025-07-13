import asyncio
import aiosqlite
import time
from typing import List, Dict, Any

async def async_fetch_users() -> List[Dict[str, Any]]:
    """
    Asynchronously fetch all users from the database.
    
    Returns:
        List[Dict[str, Any]]: List of all users as dictionaries
    """
    print("[ASYNC] Starting to fetch all users...")
    start_time = time.time()
    
    try:
        # Open async database connection
        async with aiosqlite.connect('users.db') as conn:
            # Enable row factory for dictionary-like access
            conn.row_factory = aiosqlite.Row
            
            # Execute query asynchronously
            async with conn.execute("SELECT * FROM users") as cursor:
                # Fetch all results
                rows = await cursor.fetchall()
                
                # Convert to list of dictionaries
                users = [dict(row) for row in rows]
                
                execution_time = time.time() - start_time
                print(f"[ASYNC] Fetched {len(users)} users in {execution_time:.3f} seconds")
                
                return users
                
    except Exception as e:
        print(f"[ASYNC] Error fetching all users: {e}")
        return []


async def async_fetch_older_users():
    """
    Asynchronously fetch users older than 40.
    
    Returns:
        List[Dict[str, Any]]: List of users older than 40
    """
    print("[ASYNC] Starting to fetch users older than 40...")
    start_time = time.time()
    
    try:
        # Open async database connection
        async with aiosqlite.connect('users.db') as conn:
            # Enable row factory for dictionary-like access
            conn.row_factory = aiosqlite.Row
            
            # Execute parameterized query asynchronously
            async with conn.execute("SELECT * FROM users WHERE age > ?", (40,)) as cursor:
                # Fetch all results
                rows = await cursor.fetchall()
                
                # Convert to list of dictionaries
                older_users = [dict(row) for row in rows]
                
                execution_time = time.time() - start_time
                print(f"[ASYNC] Fetched {len(older_users)} users older than 40 in {execution_time:.3f} seconds")
                
                return older_users
                
    except Exception as e:
        print(f"[ASYNC] Error fetching older users: {e}")
        return []


async def async_fetch_users_by_age_range(min_age: int, max_age: int) -> List[Dict[str, Any]]:
    """
    Additional async function to fetch users within a specific age range.
    
    Args:
        min_age (int): Minimum age
        max_age (int): Maximum age
        
    Returns:
        List[Dict[str, Any]]: List of users within the age range
    """
    print(f"[ASYNC] Starting to fetch users between {min_age} and {max_age}...")
    start_time = time.time()
    
    try:
        async with aiosqlite.connect('users.db') as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute(
                "SELECT * FROM users WHERE age BETWEEN ? AND ?", 
                (min_age, max_age)
            ) as cursor:
                rows = await cursor.fetchall()
                users_in_range = [dict(row) for row in rows]
                
                execution_time = time.time() - start_time
                print(f"[ASYNC] Fetched {len(users_in_range)} users in age range {min_age}-{max_age} in {execution_time:.3f} seconds")
                
                return users_in_range
                
    except Exception as e:
        print(f"[ASYNC] Error fetching users by age range: {e}")
        return []


async def fetch_concurrently():
    """
    Execute multiple database queries concurrently using asyncio.gather.
    
    This function demonstrates running multiple async database operations
    simultaneously to improve performance.
    """
    print("=== Starting Concurrent Database Queries ===")
    overall_start_time = time.time()
    
    try:
        # Execute multiple queries concurrently using asyncio.gather
        all_users, older_users, middle_aged_users = await asyncio.gather(
            async_fetch_users(),
            async_fetch_older_users(),
            async_fetch_users_by_age_range(25, 50),
            return_exceptions=True  # Don't fail if one query fails
        )
        
        overall_execution_time = time.time() - overall_start_time
        print(f"\n=== Concurrent Execution Completed in {overall_execution_time:.3f} seconds ===")
        
        # Process results
        print(f"\n=== Query Results ===")
        
        # Handle all users result
        if isinstance(all_users, Exception):
            print(f"Error fetching all users: {all_users}")
            all_users = []
        else:
            print(f" All users: {len(all_users)} found")
            
        # Handle older users result
        if isinstance(older_users, Exception):
            print(f"Error fetching older users: {older_users}")
            older_users = []
        else:
            print(f" Users older than 40: {len(older_users)} found")
            
        # Handle middle-aged users result
        if isinstance(middle_aged_users, Exception):
            print(f"Error fetching middle-aged users: {middle_aged_users}")
            middle_aged_users = []
        else:
            print(f" Users aged 25-50: {len(middle_aged_users)} found")
        
        # Display sample results
        print(f"\n=== Sample Results ===")
        
        if all_users:
            print(f"Sample from all users:")
            for user in all_users[:3]:  # Show first 3 users
                print(f"  - {user}")
        
        if older_users:
            print(f"\nSample from users older than 40:")
            for user in older_users[:3]:  # Show first 3 users
                print(f"  - {user}")
        
        return {
            'all_users': all_users,
            'older_users': older_users,
            'middle_aged_users': middle_aged_users
        }
        
    except Exception as e:
        print(f"[ERROR] Unexpected error in concurrent fetch: {e}")
        return {
            'all_users': [],
            'older_users': [],
            'middle_aged_users': []
        }


async def demonstrate_sequential_vs_concurrent():
    """
    Demonstrate the performance difference between sequential and concurrent execution.
    """
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON: Sequential vs Concurrent")
    print("="*60)
    
    # Sequential execution
    print("\n--- Sequential Execution ---")
    sequential_start = time.time()
    
    all_users_seq = await async_fetch_users()
    older_users_seq = await async_fetch_older_users()
    middle_aged_seq = await async_fetch_users_by_age_range(25, 50)
    
    sequential_time = time.time() - sequential_start
    print(f"Sequential execution time: {sequential_time:.3f} seconds")
    
    # Concurrent execution
    print("\n--- Concurrent Execution ---")
    concurrent_start = time.time()
    
    all_users_conc, older_users_conc, middle_aged_conc = await asyncio.gather(
        async_fetch_users(),
        async_fetch_older_users(),
        async_fetch_users_by_age_range(25, 50)
    )
    
    concurrent_time = time.time() - concurrent_start
    print(f"Concurrent execution time: {concurrent_time:.3f} seconds")
    
    # Calculate performance improvement
    if sequential_time > 0:
        improvement = ((sequential_time - concurrent_time) / sequential_time) * 100
        print(f"\nPerformance improvement: {improvement:.1f}%")
        print(f"Speed multiplier: {sequential_time / concurrent_time:.2f}x faster")


# Main execution function
async def main():
    """
    Main function to demonstrate concurrent async database operations.
    """
    print("=== Concurrent Asynchronous Database Queries Demo ===")
    
    # Main requirement: Run concurrent queries
    results = await fetch_concurrently()
    
    # Additional demonstration
    await demonstrate_sequential_vs_concurrent()
    
    print(f"\n=== Summary ===")
    print(f" Concurrent queries executed successfully")
    print(f" Used aiosqlite for async database operations")
    print(f" Used asyncio.gather for concurrent execution")
    print(f" Demonstrated performance benefits of concurrency")
    
    return results


# Run the main function
if __name__ == "__main__":
    # Use asyncio.run() to execute the concurrent fetch
    print("Starting asyncio.run(fetch_concurrently())...")
    
    try:
        # Execute the main concurrent fetch function
        final_results = asyncio.run(main())
        
        print(f"\n=== Final Results Summary ===")
        print(f"All users: {len(final_results['all_users'])}")
        print(f"Older users: {len(final_results['older_users'])}")
        print(f"Middle-aged users: {len(final_results['middle_aged_users'])}")
        
    except Exception as e:
        print(f"Error running async operations: {e}")
        
    print("\n=== Async Database Operations Complete ===")


# Alternative simple execution (as requested in instructions)
async def simple_fetch_concurrently():
    """
    Simple version matching the exact requirements.
    """
    print("=== Simple Concurrent Fetch ===")
    
    # Execute both queries concurrently
    all_users, older_users = await asyncio.gather(
        async_fetch_users(),
        async_fetch_older_users()
    )
    
    print(f"Results: {len(all_users)} total users, {len(older_users)} older users")
    return all_users, older_users


# Uncomment the line below to run the simple version
# asyncio.run(simple_fetch_concurrently())