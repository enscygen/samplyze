import sqlite3
from werkzeug.security import generate_password_hash
import os

# --- Configuration ---
# This script assumes your database is in the 'instance' folder
# and is named 'laboratory.db'.
DB_PATH = os.path.join('instance', 'laboratory.db')
ADMIN_USERNAME = 'admin'
DEFAULT_PASSWORD = 'password' # The password will be reset to this value

def reset_admin_password():
    """
    Connects to the database and resets the admin password to a default value.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'.")
        print("Please make sure you are running this script from the root of your project directory.")
        return

    try:
        # Generate the new hashed password
        hashed_password = generate_password_hash(DEFAULT_PASSWORD, method='pbkdf2:sha256')

        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Find the admin user and update their password
        cursor.execute("UPDATE user SET password_hash = ? WHERE username = ?", (hashed_password, ADMIN_USERNAME))
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            print(f"Error: Admin user '{ADMIN_USERNAME}' not found in the database.")
        else:
            conn.commit()
            print(f"Success! The password for '{ADMIN_USERNAME}' has been reset to '{DEFAULT_PASSWORD}'.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("--- Admin Password Reset Tool ---")
    # Confirmation step to prevent accidental resets
    confirm = input("Are you sure you want to reset the admin password to the default? (y/n): ")
    if confirm.lower() == 'y':
        reset_admin_password()
    else:
        print("Password reset cancelled.")
