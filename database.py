import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor # To get dict-like rows
from decouple import config
import sys # For error handling

DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL is None and 'pytest' not in sys.modules: # Check if not running tests
     print("ERROR: DATABASE_URL environment variable not set.")
     print("WARNING: DATABASE_URL not set. Falling back to local SQLite 'chatbot.db' for development.")
     import sqlite3
     DATABASE_NAME = "chatbot.db"
     def get_db_connection():
         conn = sqlite3.connect(DATABASE_NAME)
         conn.row_factory = sqlite3.Row # Keep SQLite row factory for local fallback
         return conn
     _IS_SQLITE = True # Flag to know if we're using SQLite

else:
    _IS_SQLITE = False # We are using PostgreSQL
    def get_db_connection():
        """Establishes a connection to the PostgreSQL database."""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            # Using RealDictCursor makes rows behave like dictionaries (e.g., row['id'])
            conn.cursor_factory = RealDictCursor
            return conn
        except psycopg2.OperationalError as e:
            print(f"Error connecting to PostgreSQL database: {e}")
            # In a real app, you might retry or raise a more specific exception
            raise

# --- Table Creation (Works for both PostgreSQL and SQLite fallback) ---
def create_tables():
    """Creates the necessary tables if they don't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Ensuring database tables exist...")

    try:
        # User Table (PostgreSQL syntax is mostly compatible)
        # Note: SERIAL is PostgreSQL equivalent of AUTOINCREMENT INTEGER PRIMARY KEY
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                year_of_study INTEGER
            )
        ''')

        # Courses Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                instructor TEXT NOT NULL,
                year_of_study INTEGER NOT NULL DEFAULT 1
            )
        ''')

        # Conversations Table
        # Note: TIMESTAMP DEFAULT CURRENT_TIMESTAMP works in both
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Grades Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grades (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                grade TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            DROP TABLE IF EXISTS grades CASCADE;
        ''')

        # --- Create the new 'internal_marks' table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS internal_marks (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                internal_1 INTEGER DEFAULT 0 CHECK (internal_1 >= 0 AND internal_1 <= 25),
                internal_2 INTEGER DEFAULT 0 CHECK (internal_2 >= 0 AND internal_2 <= 25),
                internal_3 INTEGER DEFAULT 0 CHECK (internal_3 >= 0 AND internal_3 <= 25),
                UNIQUE(student_id, course_id) -- A student has only one set of marks per course
            )
        ''')

        # Schedules Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                day_of_week TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT
            )
        ''')
        
        # --- NEW Enrollments Table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(student_id, course_id) -- Prevent duplicate enrollments
            )
        ''')

        # Create a 'system_config' table for settings like the prompt
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                id SERIAL PRIMARY KEY,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
        ''')

            # This PostgreSQL command inserts a default prompt IF the key 'system_prompt' doesn't exist
        cursor.execute('''
            INSERT INTO system_config (key, value)
            VALUES ('system_prompt', 'You are a helpful college chatbot.')
            ON CONFLICT (key) DO NOTHING
        ''')

        conn.commit()
        print("Database tables checked/created successfully.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error creating tables: {error}")
        conn.rollback() # Roll back changes if error occurs
    finally:
        cursor.close()
        conn.close()

def migrate_database():
    """
    Applies pending schema migrations (like adding new columns)
    to the existing database.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("Running database migrations...")

        # --- Migration 1: Add year_of_study to users table ---
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN year_of_study INTEGER")
            conn.commit()
            print("Migration successful: Added 'year_of_study' to 'users' table.")
        except (Exception, psycopg2.DatabaseError) as e:
            # Catch error if column already exists (common)
            print(f"Info (Migration 1): {e}") # Will print 'column "year_of_study" of relation "users" already exists'
            conn.rollback() # Rollback the failed ALTER TABLE transaction

        # --- Migration 2: Add year_of_study to courses table ---
        try:
            # Add the column with a default value so existing rows are not null
            cursor.execute("ALTER TABLE courses ADD COLUMN year_of_study INTEGER NOT NULL DEFAULT 1")
            conn.commit()
            print("Migration successful: Added 'year_of_study' to 'courses' table.")
        except (Exception, psycopg2.DatabaseError) as e:
            print(f"Info (Migration 2): {e}") # Will print 'column "year_of_study" of relation "courses" already exists'
            conn.rollback()

        print("Database migrations complete.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error during migration: {error}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# Keep this for local setup if needed (though startup event handles it on deploy)
if __name__ == '__main__':
     # You might want to add DATABASE_URL to your local .env file
     # pointing to your Render DB for local testing consistency
     if DATABASE_URL:
         create_tables()
     else:
         print("DATABASE_URL not set in environment. Run `python database.py` only if you need to set up the local SQLite fallback.")
         # If using SQLite fallback, you might need different create_tables logic
         # or just ensure the fallback `get_db_connection` works with the code above.
         # For simplicity, we assume PostgreSQL for the direct run now.
         # If you rely on the SQLite fallback, you might need to adjust the __main__ block.