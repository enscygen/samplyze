import sqlite3
import os

OLD_DB_PATH = os.path.join('instance', 'old_laboratory.db')
NEW_DB_PATH = os.path.join('instance', 'laboratory.db')

def migrate_data():
    """
    Dynamically discovers tables and columns to copy data from the old database to the new one,
    with special handling for the lab_settings and user tables.
    """
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: Old database file not found at '{OLD_DB_PATH}'.")
        print("Please ensure you have renamed your old database to 'old_laboratory.db'.")
        return

    if not os.path.exists(NEW_DB_PATH):
        print(f"Error: New database file not found at '{NEW_DB_PATH}'.")
        print("Please run the main application once to create the new database structure.")
        return

    old_conn = sqlite3.connect(OLD_DB_PATH)
    new_conn = sqlite3.connect(NEW_DB_PATH)
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    print("Starting data migration...")

    # Get all table names from the old database
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_names = [row[0] for row in old_cursor.fetchall()]
    
    print(f"Found tables to migrate: {', '.join(table_names)}")

    for table_name in table_names:
        try:
            print(f"  - Migrating data for table: {table_name}...")
            
            old_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in old_cursor.fetchall()]
            
            if not columns:
                print(f"    -> No columns found for table '{table_name}'. Skipping.")
                continue

            columns_str = ', '.join(columns)
            old_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
            data = old_cursor.fetchall()

            if data:
                # --- SPECIAL HANDLING FOR lab_settings ---
                if table_name == 'lab_settings':
                    print("    -> Special handling for lab_settings: Using UPDATE instead of INSERT.")
                    settings_data = data[0]
                    update_columns = [f"{col} = ?" for col in columns if col != 'id']
                    query = f"UPDATE lab_settings SET {', '.join(update_columns)} WHERE id = ?"
                    update_data = list(settings_data[1:]) + [settings_data[0]]
                    new_cursor.execute(query, update_data)
                    print(f"    -> Updated 1 row.")
                
                # --- SPECIAL HANDLING FOR user TABLE ---
                elif table_name == 'user':
                    print("    -> Special handling for user table.")
                    admin_user_data = None
                    other_users_data = []
                    
                    # Separate admin user from others
                    for row in data:
                        # Assuming the 'id' column is the first one (index 0)
                        if row[0] == 1:
                            admin_user_data = row
                        else:
                            other_users_data.append(row)
                    
                    # Update the existing admin user
                    if admin_user_data:
                        update_columns = [f"{col} = ?" for col in columns if col != 'id']
                        query = f"UPDATE user SET {', '.join(update_columns)} WHERE id = ?"
                        update_data = list(admin_user_data[1:]) + [admin_user_data[0]]
                        new_cursor.execute(query, update_data)
                        print("    -> Updated admin user row.")

                    # Insert all other users
                    if other_users_data:
                        placeholders = ', '.join(['?'] * len(columns))
                        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                        new_cursor.executemany(query, other_users_data)
                        print(f"    -> Inserted {len(other_users_data)} other user rows.")

                # --- NORMAL HANDLING FOR ALL OTHER TABLES ---
                else:
                    placeholders = ', '.join(['?'] * len(columns))
                    query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    new_cursor.executemany(query, data)
                    print(f"    -> Migrated {len(data)} rows.")
            else:
                print("    -> No data to migrate for this table.")

        except sqlite3.OperationalError as e:
            print(f"    -> Could not migrate table '{table_name}'. It might not exist in the new database. Skipping. Error: {e}")
            continue

    print("\nMigration complete. Committing changes.")
    new_conn.commit()

    old_conn.close()
    new_conn.close()

    print("Database connections closed. Your data has been migrated successfully!")

if __name__ == '__main__':
    migrate_data()
