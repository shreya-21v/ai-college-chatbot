import sqlite3

DATABASE_NAME = "chatbot.db"

def get_db_connection():
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    # This line allows you to access columns by name
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Creates the necessary tables if they don't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create a 'users' table (matches User model)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Create a 'conversations' table (matches Chat model)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create a 'courses' table (matches Course model)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            instructor TEXT NOT NULL
        )
    ''')

    # (Inside create_tables function, after CREATE TABLE courses...)

    # Create a 'grades' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')

    # Create a 'schedules' table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL, 
            start_time TEXT NOT NULL, 
            end_time TEXT NOT NULL,
            location TEXT,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')

    # These lines MUST come AFTER all the execute() commands
    print("Database tables created successfully.")
    conn.commit()
    conn.close()

    

# This allows to run this file directly to set up the database
if __name__ == '__main__':
    create_tables()