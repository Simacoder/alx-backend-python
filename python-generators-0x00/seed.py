#!/usr/bin/python3
"""
seed.py - MySQL Database Setup with Python Generators
"""

import mysql.connector
from mysql.connector import Error
import pandas as pd
import uuid
import csv
from typing import Iterator, Dict, Any, List, Union
import logging
from dotenv import load_dotenv
load_dotenv()
import os
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    HOST = os.getenv('DB_HOST', 'localhost')
    USER = os.getenv('DB_USER', 'root')
    PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE = os.getenv('DB_NAME', 'ALX_prodev')
    PORT = int(os.getenv('DB_PORT', 3306))


def connect_db() -> mysql.connector.MySQLConnection:
    try:
        connection = mysql.connector.connect(
            host=DatabaseConfig.HOST,
            user=DatabaseConfig.USER,
            password=DatabaseConfig.PASSWORD,
            port=DatabaseConfig.PORT,
            autocommit=True
        )
        if connection.is_connected():
            logger.info("Successfully connected to MySQL server")
            return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL server: {e}")
        raise
    return None


def create_database(connection: mysql.connector.MySQLConnection) -> bool:
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES LIKE %s", (DatabaseConfig.DATABASE,))
        result = cursor.fetchone()

        if result:
            logger.info(f"Database {DatabaseConfig.DATABASE} already exists")
        else:
            cursor.execute(
                f"CREATE DATABASE {DatabaseConfig.DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logger.info(f"Database {DatabaseConfig.DATABASE} created successfully")

        cursor.close()
        return True
    except Error as e:
        logger.error(f"Error creating database: {e}")
        return False


def connect_to_prodev() -> mysql.connector.MySQLConnection:
    try:
        connection = mysql.connector.connect(
            host=DatabaseConfig.HOST,
            user=DatabaseConfig.USER,
            password=DatabaseConfig.PASSWORD,
            database=DatabaseConfig.DATABASE,
            port=DatabaseConfig.PORT,
            autocommit=True
        )
        if connection.is_connected():
            logger.info(f"Successfully connected to {DatabaseConfig.DATABASE} database")
            return connection
    except Error as e:
        logger.error(f"Error connecting to {DatabaseConfig.DATABASE} database: {e}")
        raise
    return None


def create_table(connection: mysql.connector.MySQLConnection) -> bool:
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_name = 'user_data'
        """, (DatabaseConfig.DATABASE,))
        result = cursor.fetchone()

        if result[0] > 0:
            logger.info("Table user_data already exists")
        else:
            create_table_query = """
            CREATE TABLE user_data (
                user_id CHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                age DECIMAL(3,0) NOT NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_email (email),
                INDEX idx_age (age)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_query)
            logger.info("Table user_data created successfully")

        cursor.close()
        return True
    except Error as e:
        logger.error(f"Error creating table: {e}")
        return False


def insert_data(connection: mysql.connector.MySQLConnection, data) -> bool:
    """
    Insert or update data in the user_data table.

    Args:
        connection: Active MySQL connection object
        data: Either a CSV file path or a list of dictionaries containing user data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO user_data (user_id, name, email, age)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            email = VALUES(email),
            age = VALUES(age)
        """

        # If 'data' is a CSV path, read from CSV
        if isinstance(data, str):
            if not os.path.exists(data):
                logger.info(f"CSV file {data} not found. Creating sample data...")
                create_sample_csv(data, 1000)
            data = list(csv_reader_generator(data))

        # Ensure data is a list of tuples
        if isinstance(data, list) and isinstance(data[0], dict):
            data = [
                (row['user_id'], row['name'], row['email'], row['age'])
                for row in data
            ]

        cursor.executemany(insert_query, data)
        connection.commit()
        logger.info(f"Successfully inserted/updated {len(data)} records")
        cursor.close()
        return True

    except Error as e:
        logger.error(f"Error inserting data: {e}")
        return False



def generate_uuid() -> str:
    return str(uuid.uuid4())


def csv_reader_generator(file_path: str) -> Iterator[Dict[str, Any]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if 'user_id' not in row or not row['user_id']:
                    row['user_id'] = generate_uuid()

                processed_row = {
                    'user_id': str(row.get('user_id', generate_uuid())),
                    'name': str(row.get('name', '')).strip(),
                    'email': str(row.get('email', '')).strip(),
                    'age': int(float(row.get('age', 0)))
                }

                if processed_row['name'] and processed_row['email'] and processed_row['age'] > 0:
                    yield processed_row
                else:
                    logger.warning(f"Skipping invalid row: {row}")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise


def batch_insert_generator(connection: mysql.connector.MySQLConnection,
                           data_generator: Iterator[Dict[str, Any]],
                           batch_size: int = 1000) -> Iterator[int]:
    batch = []
    for record in data_generator:
        batch.append(record)
        if len(batch) >= batch_size:
            if insert_data(connection, batch):
                yield len(batch)
                batch = []
            else:
                logger.error("Failed to insert batch")
                break
    if batch:
        if insert_data(connection, batch):
            yield len(batch)


def database_row_streamer(connection: mysql.connector.MySQLConnection,
                          query: str = "SELECT * FROM user_data",
                          batch_size: int = 1000) -> Iterator[Dict[str, Any]]:
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield row
        cursor.close()
    except Error as e:
        logger.error(f"Error streaming database rows: {e}")
        raise


def create_sample_csv(file_path: str = "user_data.csv", num_records: int = 1000):
    import random
    first_names = ['Simanga', 'Mpilo', 'Zanele', 'Zakhele', 'Charlie', 'Palesa', 'Senzo', 'Frank', 'Grace', 'Henry']
    last_names = ['Zondo', 'Mlimi', 'Williams', 'Brown', 'Mthoko', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'company.com', 'example.org']

    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['user_id', 'name', 'email', 'age'])

        for _ in range(num_records):
            user_id = generate_uuid()
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            email = f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"
            age = random.randint(18, 80)
            writer.writerow([user_id, name, email, age])

    logger.info(f"Sample CSV file created: {file_path} with {num_records} records")


@contextmanager
def database_connection():
    connection = None
    try:
        connection = connect_to_prodev()
        yield connection
    finally:
        if connection and connection.is_connected():
            connection.close()
            logger.info("Database connection closed")


def stream_all_users() -> Iterator[Dict[str, Any]]:
    with connect_to_prodev() as conn:
        yield from database_row_streamer(conn)


if __name__ == "__main__":
    from time import sleep
    logger.info("Running seed.py directly...")
    connection = connect_db()
    if connection:
        create_database(connection)
        connection.close()

        connection = connect_to_prodev()
        create_table(connection)
        insert_data(connection, "user_data.csv")
        connection.close()
