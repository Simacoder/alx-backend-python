#!/usr/bin/env python3
"""
Lazy loading paginated data generator for efficient data retrieval from MySQL.
"""

import os
from dotenv import load_dotenv
import mysql.connector

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """Establish MySQL DB connection using credentials from .env"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )


def paginate_users(page_size, offset):
    """
    Fetch a page of users from the user_data table using LIMIT and OFFSET.

    Args:
        page_size (int): Number of users per page
        offset (int): Offset from the beginning of the table

    Returns:
        list of tuples: User records for the given page
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT user_id, name, email, age
            FROM user_data
            ORDER BY user_id
            LIMIT %s OFFSET %s
        """, (page_size, offset))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def lazy_pagination(page_size):
    """
    Generator that lazily fetches pages of users from the database.
    Only fetches the next page when needed.

    Args:
        page_size (int): Number of users per page

    Yields:
        list: A page of user records
    """
    offset = 0
    while True:  # Single loop required
        page = paginate_users(page_size, offset)
        if not page:
            break
        yield page
        offset += page_size


# test usage
if __name__ == "__main__":
    print("Lazy Paginated Users:\n" + "=" * 40)
    for i, page in enumerate(lazy_pagination(5), start=1):
        print(f"\nPage {i}")
        for user in page:
            print(user)
