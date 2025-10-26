from fastapi import FastAPI, Depends, HTTPException, status
from auth.router import router as auth_router

from models.schemas import Course, UserDisplay, ChatQuery, Chat # <-- Add ChatQuery and Chat
from decouple import config
import openai
# --- ADD THESE NEW IMPORTS ---
import database
from models.schemas import Course, UserDisplay
from auth.jwt import require_role, get_current_user
from typing import List
# --- END OF NEW IMPORTS ---

# This configures the OpenAI library using the key from your .env file
openai.api_key = config('OPENAI_API_KEY')
app = FastAPI()

app.include_router(auth_router, tags=["Authentication"])


@app.get("/")
def read_root():
    return {"Hello": "Backend"}


# --- THIS ENDPOINT IS NO LONGER NEEDED, WE WILL REMOVE IT ---
# We are replacing it with the functions below
# @app.get("/admin", tags=["Admin"])
# ... (you can delete the old /admin function) ...


# ===============================================
#  START OF NEW COURSES ENDPOINTS
# ===============================================

# Create dependencies for different roles
# We can reuse these in other endpoints
any_logged_in_user = Depends(get_current_user)
require_staff_or_admin = Depends(require_role(required_roles=["staff", "admin"]))


@app.post("/courses", tags=["Courses"])
def create_course(
    course: Course, 
    user: dict = require_staff_or_admin
):
    """
    Create a new course. (Staff or Admin only)
    """
    conn = database.get_db_connection()
    conn.execute(
        'INSERT INTO courses (name, description, instructor) VALUES (?, ?, ?)',
        (course.name, course.description, course.instructor)
    )
    conn.commit()
    conn.close()
    return {"message": "Course created successfully", "course": course}


@app.get("/courses", response_model=List[Course], tags=["Courses"])
def get_all_courses(user: dict = any_logged_in_user):
    """
    Get a list of all courses. (Any logged-in user)
    """
    conn = database.get_db_connection()
    courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    return [dict(course) for course in courses]


@app.get("/courses/{course_id}", response_model=Course, tags=["Courses"])
def get_course(course_id: int, user: dict = any_logged_in_user):
    """
    Get details of a specific course. (Any logged-in user)
    """
    conn = database.get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    conn.close()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return dict(course)


@app.put("/courses/{course_id}", tags=["Courses"])
def update_course(
    course_id: int, 
    course: Course, 
    user: dict = require_staff_or_admin
):
    """
    Update a course. (Staff or Admin only)
    """
    conn = database.get_db_connection()
    db_course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not db_course:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found")
        
    conn.execute(
        'UPDATE courses SET name = ?, description = ?, instructor = ? WHERE id = ?',
        (course.name, course.description, course.instructor, course_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Course updated successfully", "course": course}


@app.delete("/courses/{course_id}", tags=["Courses"])
def delete_course(course_id: int, user: dict = require_staff_or_admin):
    """
    Delete a course. (Staff or Admin only)
    """
    conn = database.get_db_connection()
    db_course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not db_course:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found")

    conn.execute('DELETE FROM courses WHERE id = ?', (course_id,))
    conn.commit()
    conn.close()
    return {"message": "Course deleted successfully"}

# ===============================================
#  START OF NEW USER MANAGEMENT ENDPOINTS
# ===============================================

# Create a dependency for admin-only access
require_admin_only = Depends(require_role(required_roles=["admin"]))

@app.get("/users", response_model=List[UserDisplay], tags=["User Management"])
def get_all_users(user: dict = require_admin_only):
    """
    Get a list of all users. (Admin only)
    """
    conn = database.get_db_connection()
    users = conn.execute('SELECT id, name, email, role FROM users').fetchall()
    conn.close()
    return [dict(u) for u in users]


@app.delete("/users/{user_id}", tags=["User Management"])
def delete_user(user_id: int, user: dict = require_admin_only):
    """
    Delete a user. (Admin only)
    """
    conn = database.get_db_connection()
    db_user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not db_user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return {"message": "User deleted successfully"}

# ===============================================
#  START OF CHATBOT ENDPOINT
# ===============================================

@app.post("/chat", response_model=Chat, tags=["Chatbot"])
def handle_chat(
    query: ChatQuery, 
    user: dict = any_logged_in_user  # 'any_logged_in_user' was defined earlier
):
    """
    Handle a user's chat query, get a response from OpenAI,
    and save the conversation. (Any logged-in user)
    """
    user_message = query.message
    user_id = user['user_id']

    # 1. FAKE AI RESPONSE (for testing without paying)
    bot_response = f"This is a test response to your message: '{user_message}'"

    # 2. Save conversation to database
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO conversations (user_id, message, response) VALUES (?, ?, ?)',
        (user_id, user_message, bot_response)
    )
    new_chat_id = cursor.lastrowid
    conn.commit()

    # 3. Get the new conversation to return it
    new_chat = conn.execute('SELECT * FROM conversations WHERE id = ?', (new_chat_id,)).fetchone()
    conn.close()

    return dict(new_chat)