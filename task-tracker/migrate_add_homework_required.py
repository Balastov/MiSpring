#!/usr/bin/env python
"""
Migration: Add homework_required column to task table
"""
import sqlite3

db_path = 'tasks.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Add homework_required column with default value True
    cursor.execute("ALTER TABLE task ADD COLUMN homework_required BOOLEAN DEFAULT 1")
    conn.commit()
    print("✓ Successfully added homework_required column to task table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("Column homework_required already exists, skipping migration")
    else:
        raise
finally:
    conn.close()
