import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor # To get dict-like rows
from decouple import config
import sys # For error handling

DATABASE_URL = config('DATABASE_URL', default=None)

# --- Check if DATABASE_URL is set ---
# This check prevents errors during local startup if the .env variable isn't set yet
# For Render deployment, the environment variable MUST be set.
if DATABASE_URL is None and 'pytest' not in sys.modules: # Check if not running tests
     print("ERROR: DATABASE_URL environment variable not set.")
     # Optionally, you could fall back to SQLite for local here,
     # but it's better to set the DATABASE_URL in your local .env too.
     # For now, we'll just exit or raise an error if it's missing during normal run.
     # raise ValueError("DATABASE_URL environment variable not set.")
     # Or provide a default local SQLite connection for development:
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
                role TEXT NOT NULL
            )
        ''')

        # Courses Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                instructor TEXT NOT NULL
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

        conn.commit()
        print("Database tables checked/created successfully.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error creating tables: {error}")
        conn.rollback() # Roll back changes if error occurs
    finally:
        cursor.close()
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