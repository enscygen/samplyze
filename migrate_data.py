import sqlite3
import os

def run_migration(new_db_path, old_db_path):
    """
    Performs the database migration.
    This function can be called from the web app or other scripts.
    Returns (True, "Success message") or (False, "Error message").
    """
    try:
        old_conn = sqlite3.connect(old_db_path)
        new_conn = sqlite3.connect(new_db_path)
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()

        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        table_names = [row[0] for row in old_cursor.fetchall()]

        migrated_tables = []
        for table_name in table_names:
            try:
                old_cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [info[1] for info in old_cursor.fetchall()]
                if not columns: continue

                columns_str = ', '.join(columns)
                old_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
                data = old_cursor.fetchall()

                if data:
                    if table_name in ['lab_settings', 'user']:
                        new_cursor.execute(f"DELETE FROM {table_name}")
                    
                    placeholders = ', '.join(['?'] * len(columns))
                    query = f"INSERT OR IGNORE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    new_cursor.executemany(query, data)
                
                migrated_tables.append(table_name)

            except sqlite3.OperationalError as e:
                print(f"Skipping table '{table_name}': {e}")
                continue
        
        new_conn.commit()
        return (True, f"Successfully migrated data from {len(migrated_tables)} tables.")

    except sqlite3.Error as e:
        return (False, f"A database error occurred during migration: {e}")
    finally:
        if 'old_conn' in locals() and old_conn: old_conn.close()
        if 'new_conn' in locals() and new_conn: new_conn.close()

