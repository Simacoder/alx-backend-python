#!/usr/bin/env python3
"""
Batch processing generator for streaming large datasets from MySQL database
"""

import os
from dotenv import load_dotenv
import mysql.connector

# Load environment variables from .env
load_dotenv()

def get_db_connection():
    """Establish MySQL connection using environment variables"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def stream_users_in_batches(batch_size):
    """
    Generator that fetches rows from the user_data table in batches.
    Yields:
        list[dict]: Batch of user records as dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT user_id, name, email, age FROM user_data")
        while True:  # Loop 1
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield batch
    finally:
        cursor.close()
        conn.close()

def batch_processing(batch_size):
    """
    Generator that yields users over age 25 from each batch
    Yields:
        list[dict]: Filtered users
    """
    for batch in stream_users_in_batches(batch_size):  # Loop 2
        filtered = [user for user in batch if user.get("age", 0) > 25]  # Loop 3
        if filtered:
            yield filtered

#  testing block
if __name__ == "__main__":
    for filtered_batch in batch_processing(50):
        for user in filtered_batch:
            print(user)
