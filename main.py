from fastapi import FastAPI, Depends, HTTPException, status
from auth.router import router as auth_router
from decouple import config
import openai
import database
from models.schemas import Course, UserDisplay, ChatQuery, Chat, CourseCreate, Grade, Schedule # <-- Add CourseCreate
from auth.jwt import require_role, get_current_user
from typing import List

# --- Simulated FAQ Database ---
FAQ_DATA = {
    "library hours": "The main library is open from 8 AM to 10 PM on weekdays and 10 AM to 6 PM on weekends.",
    "admission deadline": "The admission deadline for the next semester is November 15th. You can find more details on the admissions website.",
    "gym access": "The college gym is available to all students. You need your student ID card for access. Hours are 6 AM to 9 PM daily."
}
# --- End FAQ Database ---
openai.api_key = config('OPENAI_API_KEY')

app = FastAPI()

# This configures the OpenAI library using the key from your .env file
openai.api_key = config('OPENAI_API_KEY')
app = FastAPI()

app.include_router(auth_router, tags=["Authentication"])


@app.get("/")
def read_root():
    return {"Hello": "Backend"}

any_logged_in_user = Depends(get_current_user)
require_staff_or_admin = Depends(require_role(required_roles=["staff", "admin"]))


@app.post("/courses", tags=["Courses"])
def create_course(
    course: CourseCreate, # <-- Change this from Course
    user: dict = require_staff_or_admin
):
    # ... rest of the function remains the same ...
    conn = database.get_db_connection()
    # ... database insertion ...
    conn.close()
    # Return the input data along with the message
    return {"message": "Course created successfully", "course": course.model_dump()}


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
    course: CourseCreate, # <-- Change this from Course
    user: dict = require_staff_or_admin
):
    # ... rest of the function remains the same ...
    conn = database.get_db_connection()
    # ... database update ...
    conn.close()
     # Return the updated data along with the message
    return {"message": "Course updated successfully", "course": course.model_dump()}


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

@app.get("/users/me", response_model=UserDisplay, tags=["User Management"])
def get_current_logged_in_user(user: dict = any_logged_in_user):
    """
    Get the details of the currently logged-in user.
    """
    # The 'any_logged_in_user' dependency already fetches the user dict
    # We just need to return it.
    return user

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

@app.post("/chat", response_model=Chat, tags=["Chatbot"])
def handle_chat(
    query: ChatQuery, 
    user: dict = any_logged_in_user
):
    user_message = query.message
    user_id = user['user_id']
    
    # 1. Fetch chat history from DB (This logic is now included!)
    conn = database.get_db_connection()
    history_rows = conn.execute(
        'SELECT message, response FROM conversations WHERE user_id = ? ORDER BY timestamp ASC',
        (user_id,)
    ).fetchall()
    
    past_message_count = len(history_rows)

    # 2. FAKE AI RESPONSE (for testing without paying)
    bot_response = f"I see you have {past_message_count} past messages. My test response to '{user_message}' is: I am a mock bot."

    # 3. Save conversation to database
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO conversations (user_id, message, response) VALUES (?, ?, ?)',
        (user_id, user_message, bot_response)
    )
    new_chat_id = cursor.lastrowid
    conn.commit()
    
    # 4. Get the new conversation to return it
    new_chat = conn.execute('SELECT * FROM conversations WHERE id = ?', (new_chat_id,)).fetchone()
    conn.close()
    
    return dict(new_chat)

@app.get("/chat/history", response_model=List[Chat], tags=["Chatbot"])
def get_chat_history(user: dict = any_logged_in_user):
    """
    Get the chat history for the logged-in user.
    """
    user_id = user['id'] # <-- CORRECTED KEY
    conn = database.get_db_connection()
    history = conn.execute(
        'SELECT * FROM conversations WHERE user_id = ? ORDER BY timestamp ASC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in history]

# (Inside main.py)

# ===============================================
#  START OF GRADES ENDPOINT
# ===============================================

@app.get("/grades", response_model=List[Grade], tags=["Student Features"])
def get_student_grades(user: dict = any_logged_in_user):
    """
    Get the grades for the currently logged-in student.
    """
    if user['role'] != 'student':
         raise HTTPException(status_code=403, detail="Only students can access grades.")

    student_id = user['id']
    conn = database.get_db_connection()

    # Query grades and join with courses table to get course names
    grades_rows = conn.execute('''
        SELECT g.id, g.student_id, g.course_id, g.grade, c.name as course_name 
        FROM grades g
        JOIN courses c ON g.course_id = c.id
        WHERE g.student_id = ?
    ''', (student_id,)).fetchall()

    conn.close()
    return [dict(row) for row in grades_rows]

@app.get("/schedules", response_model=List[Schedule], tags=["Student Features"])
def get_all_schedules(user: dict = any_logged_in_user): # Allow any logged-in user
    """
    Get the schedule for all courses.
    """
    conn = database.get_db_connection()

    # Query schedules and join with courses table to get course names
    schedule_rows = conn.execute('''
        SELECT s.id, s.course_id, s.day_of_week, s.start_time, s.end_time, s.location, c.name as course_name 
        FROM schedules s
        JOIN courses c ON s.course_id = c.id
        ORDER BY c.name, s.day_of_week, s.start_time 
    ''').fetchall()

    conn.close()
    return [dict(row) for row in schedule_rows]

@app.get("/students", response_model=List[UserDisplay], tags=["Staff Features"])
def get_all_students(user: dict = require_staff_or_admin): # Use the existing dependency
    """
    Get a list of all users with the 'student' role. (Staff or Admin only)
    """
    conn = database.get_db_connection()
    students = conn.execute(
        "SELECT id, name, email, role FROM users WHERE role = 'student'"
    ).fetchall()
    conn.close()
    return [dict(s) for s in students]