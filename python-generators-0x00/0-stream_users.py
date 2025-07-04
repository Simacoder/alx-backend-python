#!/usr/bin/env python3
import os
import sys
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def stream_users():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_data")

        rows = cursor.fetchall()  # Fetch all rows to avoid unread result error
        for row in rows:
            yield row

    except Error as e:
        print(f"Error: {e}")
        return

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Make module callable like a function to match test import usage
class CallableModule:
    def __call__(self, *args, **kwargs):
        return stream_users(*args, **kwargs)

sys.modules[__name__] = CallableModule()
