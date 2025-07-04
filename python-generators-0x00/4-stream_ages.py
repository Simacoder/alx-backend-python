#!/usr/bin/env python3
"""
Memory-efficient aggregation using generators to compute average age from MySQL
"""

import os
import mysql.connector
from dotenv import load_dotenv

# Load database credentials from .env file
load_dotenv()

def get_db_connection():
    """Establish a MySQL connection using credentials from .env"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def stream_user_ages():
    """
    Generator that yields user ages one at a time from the MySQL database.

    Yields:
        int: Age of each user
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT age FROM user_data")
        # Loop 1: stream one age at a time
        for (age,) in cursor:
            if age is not None:
                yield age
    finally:
        cursor.close()
        conn.close()

def calculate_average_age():
    """
    Calculate the average age using the generator for memory efficiency.

    Returns:
        float: Average age of users (0 if none)
    """
    total = 0
    count = 0

    # Loop 2: consume the generator
    for age in stream_user_ages():
        total += age
        count += 1

    return total / count if count else 0

if __name__ == "__main__":
    avg = calculate_average_age()
    print(f"Average age of users: {avg:.2f}")
