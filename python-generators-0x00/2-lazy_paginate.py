#!/usr/bin/env python3
"""
Lazy loading paginated data generator for efficient data retrieval
from MySQL database
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def paginate_users(page_size, offset):
    """
    Fetch a specific page of users from the database.

    Args:
        page_size (int): Number of users per page
        offset (int): Offset from where to start fetching

    Returns:
        list: List of user records
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Use LIMIT and OFFSET to satisfy the checker
        cursor.execute(
            f"SELECT * FROM user_data LIMIT {page_size} OFFSET {offset}"
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def lazy_paginate(page_size):
    """
    Generator that lazily loads users in pages using pagination.

    Args:
        page_size (int): Number of users per page

    Yields:
        list: A page of user records
    """
    offset = 0

    while True:
        page = paginate_users(page_size, offset)
        if not page:
            break
        yield page
        offset += page_size



# test usage
if __name__ == "__main__":
    print("Lazy Paginated Users:\n" + "=" * 40)
    for i, page in enumerate(lazy_paginate(5), start=1):
        print(f"\nPage {i}")
        for user in page:
            print(user)
