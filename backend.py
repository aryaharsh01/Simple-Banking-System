import hashlib
import hmac
import os
import re
import sqlite3

from database import get_connection, create_tables


# Create database tables when this file is imported.
create_tables()


# ---------------- PIN FUNCTIONS ----------------

def hash_pin(pin):
    salt = os.urandom(16)
    hashed_pin = hashlib.pbkdf2_hmac(
        "sha256", pin.encode(), salt, 100000
    )
    return salt.hex() + ":" + hashed_pin.hex()


def check_pin(pin, saved_hash):
    salt_text, old_hash = saved_hash.split(":")
    salt = bytes.fromhex(salt_text)
    new_hash = hashlib.pbkdf2_hmac(
        "sha256", pin.encode(), salt, 100000
    )
    return hmac.compare_digest(bytes.fromhex(old_hash), new_hash)


# ---------------- ACCOUNT FUNCTIONS ----------------

def create_account(full_name, mobile_number, email, pin):
    full_name = str(full_name).strip()
    mobile_number = str(mobile_number).strip()
    email = str(email).strip().lower()
    pin = str(pin).strip()

    if not full_name or not mobile_number or not email:
        return False, "Please fill all details."

    if not mobile_number.isdigit() or len(mobile_number) != 10:
        return False, "Mobile number must contain 10 digits."

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Enter a valid email address."

    if not pin.isdigit() or len(pin) != 4:
        return False, "PIN must contain 4 digits."

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO accounts
            (full_name, mobile_number, email, pin_hash)
            VALUES (?, ?, ?, ?)
        """, (full_name, mobile_number, email, hash_pin(pin)))

        account_number = cursor.lastrowid 
        connection.commit()
        return True, account_number

    except sqlite3.IntegrityError:
        connection.rollback()
        return False, "Mobile number or email already exists."
    finally:
        connection.close()


def login(account_number, pin):
    if not str(account_number).isdigit() or not str(pin).isdigit():
        return False, "Invalid account number or PIN."

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT account_number, full_name, mobile_number,
                   email, pin_hash, balance, status
            FROM accounts
            WHERE account_number = ?
        """, (int(account_number),))
        account = cursor.fetchone()

        if account is None:
            return False, "Account not found."

        if account["status"] != "ACTIVE":
            return False, "Account is not active."

        if check_pin(str(pin), account["pin_hash"]):
            user = dict(account)
            user.pop("pin_hash")
            return True, user

        return False, "Incorrect PIN."
    finally:
        connection.close()


def logout(session_state):
    """Clear login details from Streamlit session state."""
    for key in ["logged_in", "account_number", "user_name", "user_data"]:
        session_state.pop(key, None)
    return True, "Logged out successfully."


# ---------------- BALANCE ----------------

def check_balance(account_number):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT balance FROM accounts
            WHERE account_number = ? AND status = 'ACTIVE'
        """, (account_number,))
        result = cursor.fetchone()

        if result is None:
            return False, "Account not found."

        return True, result["balance"]
    finally:
        connection.close()


# ---------------- TRANSACTION HELPER ----------------

def add_transaction(cursor, account_number, transaction_type,
                    amount, balance_after, description="",
                    receiver_account=None):
    cursor.execute("""
        INSERT INTO transactions
        (account_number, transaction_type, amount, description,
         balance_after, receiver_account)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        account_number, transaction_type, amount, description,
        balance_after, receiver_account
    ))


# ---------------- DEPOSIT ----------------

def deposit_money(account_number, amount):
    try:
        amount = round(float(amount), 2)
    except (ValueError, TypeError):
        return False, "Enter a valid amount."

    if amount <= 0:
        return False, "Amount must be greater than zero."

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE accounts
            SET balance = balance + ?
            WHERE account_number = ? AND status = 'ACTIVE'
        """, (amount, account_number))

        if cursor.rowcount == 0:
            connection.rollback()
            return False, "Account not found."

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_number = ?",
            (account_number,)
        )
        balance = cursor.fetchone()["balance"]

        add_transaction(
            cursor, account_number, "DEPOSIT",
            amount, balance, "Money deposited"
        )
        connection.commit()
        return True, "Deposit successful."
    except Exception:
        connection.rollback()
        return False, "Deposit failed."
    finally:
        connection.close()


# ---------------- WITHDRAW ----------------

def withdraw_money(account_number, amount):
    try:
        amount = round(float(amount), 2)
    except (ValueError, TypeError):
        return False, "Enter a valid amount."

    if amount <= 0:
        return False, "Amount must be greater than zero."

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE accounts
            SET balance = balance - ?
            WHERE account_number = ?
              AND status = 'ACTIVE'
              AND balance >= ?
        """, (amount, account_number, amount))

        if cursor.rowcount == 0:
            connection.rollback()
            return False, "Account not found or insufficient balance."

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_number = ?",
            (account_number,)
        )
        balance = cursor.fetchone()["balance"]

        add_transaction(
            cursor, account_number, "WITHDRAWAL",
            amount, balance, "Money withdrawn"
        )
        connection.commit()
        return True, "Withdrawal successful."
    except Exception:
        connection.rollback()
        return False, "Withdrawal failed."
    finally:
        connection.close()


# ---------------- SEND MONEY ----------------

def send_money(sender_account, receiver_account, amount):
    try:
        amount = round(float(amount), 2)
    except (ValueError, TypeError):
        return False, "Enter a valid amount."

    if amount <= 0:
        return False, "Amount must be greater than zero."

    if str(sender_account) == str(receiver_account):
        return False, "You cannot send money to your own account."

    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT account_number FROM accounts
            WHERE account_number = ? AND status = 'ACTIVE'
        """, (receiver_account,))
        if cursor.fetchone() is None:
            return False, "Receiver account not found."

        cursor.execute("""
            UPDATE accounts
            SET balance = balance - ?
            WHERE account_number = ?
              AND status = 'ACTIVE'
              AND balance >= ?
        """, (amount, sender_account, amount))

        if cursor.rowcount == 0:
            connection.rollback()
            return False, "Sender account not found or insufficient balance."

        cursor.execute("""
            UPDATE accounts
            SET balance = balance + ?
            WHERE account_number = ? AND status = 'ACTIVE'
        """, (amount, receiver_account))

        if cursor.rowcount == 0:
            connection.rollback()
            return False, "Receiver account could not be updated."

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_number = ?",
            (sender_account,)
        )
        sender_balance = cursor.fetchone()["balance"]

        cursor.execute(
            "SELECT balance FROM accounts WHERE account_number = ?",
            (receiver_account,)
        )
        receiver_balance = cursor.fetchone()["balance"]

        add_transaction(
            cursor, sender_account, "TRANSFER_SENT",
            amount, sender_balance,
            "Money sent to account " + str(receiver_account),
            receiver_account
        )
        add_transaction(
            cursor, receiver_account, "TRANSFER_RECEIVED",
            amount, receiver_balance,
            "Money received from account " + str(sender_account),
            sender_account
        )

        connection.commit()
        return True, "Money transferred successfully."
    except Exception:
        connection.rollback()
        return False, "Transfer failed."
    finally:
        connection.close()


# ---------------- TRANSACTION HISTORY ----------------

def transaction_history(account_number):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT transaction_id, transaction_type, amount,
                   transaction_date, description, balance_after,
                   receiver_account
            FROM transactions
            WHERE account_number = ?
            ORDER BY transaction_id DESC
        """, (account_number,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


# ---------------- ACCOUNT REPORT ----------------

def account_report(account_number):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT account_number, full_name, mobile_number,
                   email, balance, created_at, status
            FROM accounts
            WHERE account_number = ?
        """, (account_number,))
        account = cursor.fetchone()

        if account is None:
            return False, "Account not found."

        cursor.execute("""
            SELECT COUNT(*) AS total_transactions
            FROM transactions
            WHERE account_number = ?
        """, (account_number,))
        total = cursor.fetchone()["total_transactions"]

        report = dict(account)
        report["total_transactions"] = total
        return True, report
    finally:
        connection.close()
