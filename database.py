import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor # To get dict-like rows
from decouple import config
import sys # For error handling

DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL is None and 'pytest' not in sys.modules: 
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
            conn.cursor_factory = RealDictCursor
            return conn
        except psycopg2.OperationalError as e:
            print(f"Error connecting to PostgreSQL database: {e}")
            raise

# --- Table Creation ---
def create_tables():
    """Creates the necessary tables if they don't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Ensuring database tables exist...")

    try:
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

        # Internal_marks table 
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

        # System_config table 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                id SERIAL PRIMARY KEY,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
        ''')

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

if __name__ == '__main__':
    
     if DATABASE_URL:
         create_tables()
     else:
         print("DATABASE_URL not set in environment. Run `python database.py` only if you need to set up the local SQLite fallback.")
        