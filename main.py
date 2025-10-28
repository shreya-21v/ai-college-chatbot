from fastapi import FastAPI, Depends, HTTPException, status
from auth.router import router as auth_router
from decouple import config
import openai
import database
from models.schemas import Course, UserDisplay, ChatQuery, Chat, CourseCreate, Grade, Schedule, GradeCreate, ScheduleCreate # <-- Add CourseCreate
from auth.jwt import require_role, get_current_user
from typing import List
from langdetect import detect, LangDetectException # <-- Add this import
from collections import Counter # <-- Add this import at the top
import urllib.parse

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
    course: CourseCreate, 
    user: dict = require_staff_or_admin
):
    """
    Create a new course. (Staff or Admin only)
    """
    conn = database.get_db_connection()
    try:
        conn.execute(
            'INSERT INTO courses (name, description, instructor) VALUES (?, ?, ?)',
            (course.name, course.description, course.instructor)
        )
        conn.commit() # <-- MAKE SURE THIS LINE IS HERE AND INDENTED CORRECTLY
    except Exception as e:
         # It's good practice to close connection even if error occurs
         conn.close() 
         # Re-raise or handle specific database errors if needed
         raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
         # Ensure connection is always closed
         if conn:
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
    user_id = user['id']

    # --- Start Language Detection ---
    detected_language = "en" # Default to English
    try:
        detected_language = detect(user_message)
    except LangDetectException:
        print("Language detection failed, defaulting to English.")
    # --- End Language Detection ---


    # --- Start FAQ Logic ---
    faq_context = ""
    user_msg_lower = user_message.lower()
    faq_keywords = {
        "library hours": ["library", "hours", "open", "close"],
        "admission deadline": ["admission", "deadline", "apply", "application"],
        "gym access": ["gym", "fitness", "sports", "access"]
    }
    for faq_key, keywords in faq_keywords.items():
        if any(word in user_msg_lower for word in keywords):
            faq_context = f"Relevant Information: {FAQ_DATA[faq_key]}"
            break
    # --- End FAQ Logic ---

    # 1. Fetch chat history from DB
    conn = database.get_db_connection()
    history_rows = conn.execute(
        'SELECT message, response FROM conversations WHERE user_id = ? ORDER BY timestamp ASC',
        (user_id,)
    ).fetchall()
    past_message_count = len(history_rows)

    # --- Build messages for OpenAI ---
    # Modify system prompt based on language
    system_prompt = f"You are a helpful college chatbot. Please respond in {detected_language}." # <-- Language instruction
    if faq_context:
        system_prompt += f" {faq_context}" # Append context

    messages = [{"role": "system", "content": system_prompt}]
    for row in history_rows:
        messages.append({"role": "user", "content": row['message']})
        messages.append({"role": "assistant", "content": row['response']})
    messages.append({"role": "user", "content": user_message})
    # --- End building messages ---


    # --- Modify the MOCK response to include language ---
    # 2. FAKE AI RESPONSE
    language_note = f"(Detected Language: {detected_language})"
    if faq_context:
         bot_response = f"{language_note} (Using FAQ Context) My test response to '{user_message}' is: I am a mock bot using provided info."
    else:
        bot_response = f"{language_note} I see you have {past_message_count} past messages. My test response to '{user_message}' is: I am a mock bot."
    # --- End modify mock response ---

    # --- The real OpenAI call (would use the updated 'messages') ---
    #try:
        #completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        #bot_response = completion.choices[0].message.content
    #except Exception as e:
        #print(f"Error calling OpenAI: {str(e)}")
        # Fallback to mock response if API call fails
        #bot_response = "I apologize, but I'm having trouble processing your request right now."
    # --- End real OpenAI call ---


    # 3. Save conversation to database
    # ... (database saving code remains the same) ...
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO conversations (user_id, message, response) VALUES (?, ?, ?)',
        (user_id, user_message, bot_response)
    )
    new_chat_id = cursor.lastrowid
    conn.commit()

    # 4. Get the new conversation to return it
    # ... (database fetching code remains the same) ...
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

@app.get("/reports/grade-distribution", tags=["Reports"])
def get_grade_distribution_report(user: dict = require_staff_or_admin):
    """
    Generates a report showing grade distribution for each course.
    (Staff or Admin only)
    """
    conn = database.get_db_connection()

    # Fetch all courses
    courses = conn.execute("SELECT id, name FROM courses").fetchall()

    report_data = {}

    for course in courses:
        course_id = course['id']
        course_name = course['name']

        # Fetch grades for this specific course
        grades = conn.execute(
            "SELECT grade FROM grades WHERE course_id = ?",
            (course_id,)
        ).fetchall()

        # Count the occurrences of each grade
        grade_counts = Counter(row['grade'] for row in grades)

        # Store the counts for this course
        report_data[course_name] = dict(grade_counts)

    conn.close()
    return report_data

# (Inside main.py)

# ===============================================
#  START OF ADMIN FEATURES ENDPOINTS
# ===============================================

@app.get("/analytics/usage", tags=["Admin Features"])
def get_usage_analytics(user: dict = require_admin_only): # Use admin-only dependency
    """
    Get basic usage statistics. (Admin only)
    """
    conn = database.get_db_connection()

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    total_conversations = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "total_courses": total_courses,
        "total_conversations": total_conversations
    }
# (Inside main.py, e.g., after the GET /grades endpoint)

@app.post("/grades", tags=["Staff Features"]) # Changed tag
def add_student_grade(
    grade_data: GradeCreate,
    user: dict = require_staff_or_admin # Staff/Admin only
):
    """Adds a grade for a student in a course."""
    conn = database.get_db_connection()
    # Optional: Add checks here to ensure student_id and course_id exist
    try:
        conn.execute(
            "INSERT INTO grades (student_id, course_id, grade) VALUES (?, ?, ?)",
            (grade_data.student_id, grade_data.course_id, grade_data.grade)
        )
        conn.commit()
    except database.sqlite3.IntegrityError as e: # Catch potential foreign key errors
         conn.close()
         raise HTTPException(status_code=400, detail=f"Invalid student or course ID: {e}")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

    return {"message": "Grade added successfully"}

# (Inside main.py, e.g., after the GET /schedules endpoint)

@app.post("/schedules", tags=["Staff Features"]) # Changed tag
def add_course_schedule(
    schedule_data: ScheduleCreate,
    user: dict = require_staff_or_admin # Staff/Admin only
):
    """Adds a schedule entry for a course."""
    conn = database.get_db_connection()
    # Optional: Add check here to ensure course_id exists
    try:
        conn.execute(
            """INSERT INTO schedules
               (course_id, day_of_week, start_time, end_time, location)
               VALUES (?, ?, ?, ?, ?)""",
            (schedule_data.course_id, schedule_data.day_of_week,
             schedule_data.start_time, schedule_data.end_time, schedule_data.location)
        )
        conn.commit()
    except database.sqlite3.IntegrityError as e: # Catch potential foreign key errors
         conn.close()
         raise HTTPException(status_code=400, detail=f"Invalid course ID: {e}")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

    return {"message": "Schedule entry added successfully"}

@app.get("/schedules/instructor/{instructor_name}", response_model=List[Schedule], tags=["Student Features", "Staff Features"])
def get_instructor_schedule(instructor_name: str, user: dict = any_logged_in_user):
    """
    Get the teaching schedule for a specific instructor.
    Decodes the instructor name from the URL.
    """
    # Decode the instructor name from the URL (handles spaces, etc.)
    decoded_instructor_name = urllib.parse.unquote(instructor_name)

    conn = database.get_db_connection()

    # Query schedules by joining with courses and filtering by instructor name
    schedule_rows = conn.execute('''
        SELECT s.id, s.course_id, s.day_of_week, s.start_time, s.end_time, s.location, c.name as course_name 
        FROM schedules s
        JOIN courses c ON s.course_id = c.id
        WHERE c.instructor = ? 
        ORDER BY s.day_of_week, s.start_time 
    ''', (decoded_instructor_name,)).fetchall()

    conn.close()
    return [dict(row) for row in schedule_rows]