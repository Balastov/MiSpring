#!/usr/bin/env python
"""
Migration: Add Telegram integration fields to user and task tables
"""
import sqlite3

db_path = 'tasks.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Adding Telegram fields to user table...")

    # Add telegram_id (unique)
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN telegram_id TEXT")
        print("  ✓ Added telegram_id")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  - telegram_id already exists, skipping")
        else:
            raise

    # Add telegram_username
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN telegram_username TEXT")
        print("  ✓ Added telegram_username")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  - telegram_username already exists, skipping")
        else:
            raise

    # Add telegram_code (unique)
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN telegram_code TEXT")
        print("  ✓ Added telegram_code")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  - telegram_code already exists, skipping")
        else:
            raise

    # Add telegram_notifications (default True)
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN telegram_notifications BOOLEAN DEFAULT 1")
        print("  ✓ Added telegram_notifications")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  - telegram_notifications already exists, skipping")
        else:
            raise

    print("\nAdding student_confirmed field to task table...")

    # Add student_confirmed to task
    try:
        cursor.execute("ALTER TABLE task ADD COLUMN student_confirmed BOOLEAN DEFAULT 0")
        print("  ✓ Added student_confirmed")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  - student_confirmed already exists, skipping")
        else:
            raise

    conn.commit()
    print("\n✅ Migration completed successfully!")

except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    conn.rollback()
    raise
finally:
    conn.close()
