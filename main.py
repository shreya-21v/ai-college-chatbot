from fastapi import FastAPI, Depends, HTTPException, status
from auth.router import router as auth_router
from decouple import config
import database # Import the refactored database module
from models.schemas import ( # Using parenthesis for multiple lines
    Course, UserDisplay, ChatQuery, Chat, CourseCreate, Grade, Schedule,
    GradeCreate, ScheduleCreate
)
from auth.jwt import require_role, get_current_user # These are updated for psycopg2
from typing import List
from langdetect import detect, LangDetectException
from collections import Counter
import urllib.parse
from database import create_tables

# --- NEW: Google Gemini API Setup ---
import google.generativeai as genai
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default=None)
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    print("Warning: GOOGLE_API_KEY not found. Chatbot AI will not function.")
# --- End Gemini Setup ---


# --- Simulated FAQ Database ---
FAQ_DATA = {
    "library hours": "The main library is open from 8 AM to 10 PM on weekdays and 10 AM to 6 PM on weekends.",
    "admission deadline": "The admission deadline for the next semester is November 15th. You can find more details on the admissions website.",
    "gym access": "The college gym is available to all students. You need your student ID card for access. Hours are 6 AM to 9 PM daily."
}
# --- End FAQ Database ---

app = FastAPI()

# --- Database Initialization on Startup ---
@app.on_event("startup")
def on_startup():
    print("Running startup tasks...")
    try:
         create_tables() # Call the function from database.py
         print("Startup tasks complete.")
    except Exception as e:
         print(f"Error during startup task create_tables: {e}")

# Include Authentication Router
app.include_router(auth_router, tags=["Authentication"])

# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"Hello": "Backend"}

# --- Dependencies ---
any_logged_in_user = Depends(get_current_user)
require_staff_or_admin = Depends(require_role(required_roles=["staff", "admin"]))
require_admin_only = Depends(require_role(required_roles=["admin"]))


# ===============================================
#  COURSES ENDPOINTS
# ===============================================

@app.post("/courses", tags=["Courses"])
def create_course(
    course: CourseCreate,
    user: dict = require_staff_or_admin
):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO courses (name, description, instructor) VALUES (%s, %s, %s)',
            (course.name, course.description, course.instructor)
        )
        conn.commit()
        return {"message": "Course created successfully", "course": course.model_dump()}
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error creating course: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error creating course.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/courses", response_model=List[Course], tags=["Courses"])
def get_all_courses(user: dict = any_logged_in_user):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, instructor FROM courses')
        courses = cursor.fetchall() # RealDictCursor returns list of dicts
        return courses
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching courses: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching courses.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/courses/{course_id}", response_model=Course, tags=["Courses"])
def get_course(course_id: int, user: dict = any_logged_in_user):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, instructor FROM courses WHERE id = %s', (course_id,))
        course = cursor.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        return course
    except HTTPException:
         raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching course {course_id}: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching course.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.put("/courses/{course_id}", tags=["Courses"])
def update_course(
    course_id: int,
    course: CourseCreate,
    user: dict = require_staff_or_admin
):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM courses WHERE id = %s', (course_id,))
        db_course = cursor.fetchone()
        if not db_course:
            raise HTTPException(status_code=404, detail="Course not found")

        cursor.execute(
            'UPDATE courses SET name = %s, description = %s, instructor = %s WHERE id = %s',
            (course.name, course.description, course.instructor, course_id)
        )
        conn.commit()
        return {"message": "Course updated successfully", "course": course.model_dump()}
    except HTTPException:
         raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error updating course {course_id}: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error updating course.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.delete("/courses/{course_id}", tags=["Courses"])
def delete_course(course_id: int, user: dict = require_staff_or_admin):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM courses WHERE id = %s', (course_id,))
        db_course = cursor.fetchone()
        if not db_course:
            raise HTTPException(status_code=404, detail="Course not found")

        cursor.execute('DELETE FROM courses WHERE id = %s', (course_id,))
        conn.commit()
        return {"message": "Course deleted successfully"}
    except HTTPException:
         raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error deleting course {course_id}: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error deleting course.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ===============================================
#  USER MANAGEMENT ENDPOINTS
# ===============================================

@app.get("/users", response_model=List[UserDisplay], tags=["User Management"])
def get_all_users(user: dict = require_admin_only):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email, role FROM users')
        users = cursor.fetchall()
        return users
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching all users: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching users.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/users/me", response_model=UserDisplay, tags=["User Management"])
def get_current_logged_in_user(user: dict = any_logged_in_user):
    return user

@app.delete("/users/{user_id}", tags=["User Management"])
def delete_user(user_id: int, user: dict = require_admin_only):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        db_user = cursor.fetchone()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        return {"message": "User deleted successfully"}
    except HTTPException:
         raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error deleting user {user_id}: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error deleting user.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ===============================================
#  CHATBOT ENDPOINT (*** UPDATED FOR GEMINI ***)
# ===============================================

@app.post("/chat", response_model=Chat, tags=["Chatbot"])
def handle_chat(
    query: ChatQuery,
    user: dict = any_logged_in_user
):
    user_message = query.message
    user_id = user['id'] # Use 'id' from the user dict

    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="AI service is not configured.")

    # --- Language Detection ---
    detected_language = "en"
    try:
        detected_language = detect(user_message)
    except LangDetectException:
        print("Language detection failed, defaulting to English.")

    # --- FAQ Logic ---
    faq_context = ""
    user_msg_lower = user_message.lower()
    faq_keywords = {
        "library hours": ["library", "hours", "open", "close"],
        "admission deadline": ["admission", "deadline", "apply", "application"],
        "gym access": ["gym", "fitness", "sports", "access"]
    }
    for faq_key, keywords in faq_keywords.items():
        if any(word in user_msg_lower for word in keywords):
            faq_context = f"Relevant Information: {FAQ_DATA[faq_key]}"; break

    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch chat history from DB
        cursor.execute(
            'SELECT message, response FROM conversations WHERE user_id = %s ORDER BY timestamp ASC',
            (user_id,)
        )
        history_rows = cursor.fetchall()
        
        # --- Build messages for Gemini ---
        system_prompt = f"You are a helpful college chatbot. Please respond in {detected_language}."
        if faq_context:
            system_prompt += f" {faq_context}"
        
        # Format history for Gemini
        gemini_history = []
        for row in history_rows:
            gemini_history.append({"role": "user", "parts": [{"text": row['message']}]})
            gemini_history.append({"role": "model", "parts": [{"text": row['response']}]})

        # --- Real Google Gemini API Call ---
        try:
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash-preview-09-2025', # Using a capable free-tier model
                system_instruction=system_prompt
            )
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(user_message)
            bot_response = response.text
            
        except Exception as e:
            print(f"Google Gemini API error: {e}")
            raise HTTPException(status_code=500, detail="Error connecting to AI service.")
        # --- End Real AI Call ---

        # 3. Save conversation to database
        cursor.execute(
            'INSERT INTO conversations (user_id, message, response) VALUES (%s, %s, %s) RETURNING id',
            (user_id, user_message, bot_response)
        )
        new_chat_id_row = cursor.fetchone()
        if not new_chat_id_row: raise HTTPException(status_code=500, detail="Failed to save chat.")
        new_chat_id = new_chat_id_row['id']
        conn.commit()

        # 4. Get the new conversation to return it
        cursor.execute('SELECT * FROM conversations WHERE id = %s', (new_chat_id,))
        new_chat = cursor.fetchone()
        if not new_chat: raise HTTPException(status_code=404, detail="Saved chat not found.")
        return new_chat

    except HTTPException: raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error handling chat: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error handling chat.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/chat/history", response_model=List[Chat], tags=["Chatbot"])
def get_chat_history(user: dict = any_logged_in_user):
    user_id = user['id']
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM conversations WHERE user_id = %s ORDER BY timestamp ASC',
            (user_id,)
        )
        history = cursor.fetchall()
        return history
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching chat history: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching chat history.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ===============================================
#  STUDENT FEATURES ENDPOINTS
# ===============================================

@app.get("/grades", response_model=List[Grade], tags=["Student Features"])
def get_student_grades(user: dict = any_logged_in_user):
    if user['role'] != 'student': raise HTTPException(status_code=403, detail="Only students can access grades.")
    student_id = user['id']
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.id, g.student_id, g.course_id, g.grade, c.name as course_name
            FROM grades g JOIN courses c ON g.course_id = c.id
            WHERE g.student_id = %s
        ''', (student_id,))
        grades_rows = cursor.fetchall()
        return grades_rows
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching grades: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching grades.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/schedules", response_model=List[Schedule], tags=["Student Features"])
def get_all_schedules(user: dict = any_logged_in_user):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.course_id, s.day_of_week, s.start_time, s.end_time, s.location, c.name as course_name
            FROM schedules s JOIN courses c ON s.course_id = c.id
            ORDER BY c.name, s.day_of_week, s.start_time
        ''')
        schedule_rows = cursor.fetchall()
        return schedule_rows
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching schedules: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching schedules.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/schedules/instructor/{instructor_name}", response_model=List[Schedule], tags=["Student Features", "Staff Features"])
def get_instructor_schedule(instructor_name: str, user: dict = any_logged_in_user):
    decoded_instructor_name = urllib.parse.unquote(instructor_name)
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.course_id, s.day_of_week, s.start_time, s.end_time, s.location, c.name as course_name
            FROM schedules s JOIN courses c ON s.course_id = c.id
            WHERE c.instructor = %s ORDER BY s.day_of_week, s.start_time
        ''', (decoded_instructor_name,))
        schedule_rows = cursor.fetchall()
        return schedule_rows
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching instructor schedule: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching instructor schedule.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ===============================================
#  STAFF FEATURES ENDPOINTS
# ===============================================

@app.get("/students", response_model=List[UserDisplay], tags=["Staff Features"])
def get_all_students(user: dict = require_staff_or_admin):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role FROM users WHERE role = 'student'")
        students = cursor.fetchall()
        return students
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching students: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching students.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.post("/grades", tags=["Staff Features"])
def add_student_grade(
    grade_data: GradeCreate,
    user: dict = require_staff_or_admin
):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO grades (student_id, course_id, grade) VALUES (%s, %s, %s)",
            (grade_data.student_id, grade_data.course_id, grade_data.grade)
        )
        conn.commit()
        return {"message": "Grade added successfully"}
    except database.psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid student or course ID: {e}")
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error adding grade: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error adding grade.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.post("/schedules", tags=["Staff Features"])
def add_course_schedule(
    schedule_data: ScheduleCreate,
    user: dict = require_staff_or_admin
):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO schedules
               (course_id, day_of_week, start_time, end_time, location)
               VALUES (%s, %s, %s, %s, %s)""",
            (schedule_data.course_id, schedule_data.day_of_week,
             schedule_data.start_time, schedule_data.end_time, schedule_data.location)
        )
        conn.commit()
        return {"message": "Schedule entry added successfully"}
    except database.psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid course ID: {e}")
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error adding schedule: {error}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Database error adding schedule.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ===============================================
#  REPORTS ENDPOINT
# ===============================================

@app.get("/reports/grade-distribution", tags=["Reports"])
def get_grade_distribution_report(user: dict = require_staff_or_admin):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM courses")
        courses = cursor.fetchall()
        report_data = {}
        for course in courses:
            course_id = course['id']
            course_name = course['name']
            cursor.execute("SELECT grade FROM grades WHERE course_id = %s", (course_id,))
            grades = cursor.fetchall()
            grade_counts = Counter(row['grade'] for row in grades)
            report_data[course_name] = dict(grade_counts)
        return report_data
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error generating grade report: {error}")
        raise HTTPException(status_code=500, detail="Database error generating grade report.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ===============================================
#  ADMIN FEATURES ENDPOINTS
# ===============================================

@app.get("/analytics/usage", tags=["Admin Features"])
def get_usage_analytics(user: dict = require_admin_only):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) FROM courses")
        total_courses = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()['count']
        return {
            "total_users": total_users,
            "total_courses": total_courses,
            "total_conversations": total_conversations
        }
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching usage analytics: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching usage analytics.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.get("/analytics/conversations-per-student", tags=["Admin Features"])
def get_conversations_per_student(user: dict = require_admin_only):
    conn = None; cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.name, u.email, COUNT(c.id) as message_count
            FROM users u LEFT JOIN conversations c ON u.id = c.user_id
            WHERE u.role = 'student'
            GROUP BY u.id, u.name, u.email
            ORDER BY message_count DESC
        ''')
        usage_data = cursor.fetchall()
        return usage_data
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"DB Error fetching conversation analytics: {error}")
        raise HTTPException(status_code=500, detail="Database error fetching conversation analytics.")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
