
import sqlite3

DATABASE_NAME = "banking.db"


# Database Connection
def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# Create Database Tables
def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_number INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            mobile_number TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            pin_hash TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0 CHECK (balance >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'ACTIVE'
        )
    """)

    # Start Account Number from 1001
    cursor.execute("""
        UPDATE sqlite_sequence
        SET seq = 1000
        WHERE name = 'accounts' AND seq < 1000
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO sqlite_sequence (name, seq)
        VALUES ('accounts', 1000)
    """)

    # Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            transaction_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            balance_after REAL NOT NULL,
            receiver_account INTEGER,
            FOREIGN KEY (account_number)
                REFERENCES accounts(account_number),
            FOREIGN KEY (receiver_account)
                REFERENCES accounts(account_number)
        )
    """)

    connection.commit()
    connection.close()


# Run Database
if __name__ == "__main__":
    create_tables()
    print("Database created successfully.")
