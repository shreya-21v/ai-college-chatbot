import streamlit as st
import requests
import urllib.parse # For instructor schedules

# --- Configuration ---
BACKEND_URL = "https://ai-college-chatbot-backend.onrender.com"  # Your public Render backend URL

# --- Utility Functions ---

def login_user(username, password):
    """Attempts to log in the user via the FastAPI backend."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/login",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state['access_token'] = data['access_token']
            st.session_state['logged_in'] = True
            
            token = f"Bearer {data['access_token']}"
            headers = {"Authorization": token} # Use these headers for next calls

            # --- Get user details ---
            user_details_response = requests.get(
                f"{BACKEND_URL}/users/me", 
                headers=headers 
            )
            if user_details_response.status_code == 200:
                user_details = user_details_response.json()
                st.session_state['user_role'] = user_details.get('role')
                st.session_state['user_name'] = user_details.get('name', 'user') # Store name
            else:
                print(f"Error fetching user details: {user_details_response.status_code}")
                st.session_state['user_role'] = 'user' 
                st.session_state['user_name'] = 'user'
            
            # --- Fetch chat history ---
            history_response = requests.get(
                f"{BACKEND_URL}/chat/history",
                headers=headers 
            )
            if history_response.status_code == 200:
                history_data = history_response.json()
                st.session_state['chat_history'] = [{"user": row['message'], "bot": row['response']} for row in history_data]
            else:
                print(f"Error fetching chat history: {history_response.status_code}")
                st.session_state['chat_history'] = [] # Start fresh if history fails

            st.rerun() 
        else:
            st.error("Invalid username or password")
    except requests.ConnectionError:
        st.error("Failed to connect to the backend. Is it running?")
    except Exception as e:
        st.error(f"An error occurred during login: {e}")

def logout_user():
    """Logs out the user by clearing the session state."""
    keys_to_clear = ['logged_in', 'access_token', 'user_role', 'user_name', 'chat_history']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def get_chat_response(message):
    """Sends a message to the chat API and gets a response."""
    if 'access_token' not in st.session_state:
        st.error("You are not logged in.")
        return None
    
    token = f"Bearer {st.session_state['access_token']}"
    headers = {"Authorization": token}
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": message},
            headers=headers
        )
        if response.status_code == 200:
            return response.json()['response']
        else:
            st.error(f"Error from chat API: {response.text}")
            return None
    except Exception as e:
        st.error(f"An error occurred while chatting: {e}")
        return None

# --- Main App Logic ---

st.set_page_config(page_title="College AI Chatbot", layout="wide")

# Initialize session state if it doesn't exist
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# --- 1. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.title("Welcome to the AI College Chatbot")
    
    col1, col2 = st.columns(2) # Create two columns for layout

    with col1: # Login form in the left column
        st.subheader("Please log in")
        with st.form("login_form"):
            username = st.text_input("Email (Username)")
            password = st.text_input("Password", type="password")
            submitted_login = st.form_submit_button("Login")
            
            if submitted_login:
                login_user(username, password)

    with col2: # Registration form in the right column
        st.subheader("New Student? Register Here")
        with st.form("register_form", clear_on_submit=True):
            reg_name = st.text_input("Full Name")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Choose Password", type="password")
            # Automatically set role to 'student' for self-registration
            reg_role = "student" 
            submitted_register = st.form_submit_button("Register")

            if submitted_register:
                if not reg_name or not reg_email or not reg_password:
                    st.warning("Please fill out all registration fields.")
                else:
                    user_data = {
                        "name": reg_name,
                        "email": reg_email,
                        "password": reg_password,
                        "role": reg_role 
                    }
                    try:
                        response = requests.post(f"{BACKEND_URL}/register", json=user_data)
                        if response.status_code == 200: # FastAPI register returns 200
                            st.success("Registration successful! Please log in.")
                        elif response.status_code == 400: # Bad request (e.g., email exists)
                            st.error(f"Registration failed: {response.json().get('detail', 'Unknown error')}")
                        else:
                            st.error(f"Registration failed with code {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"Error during registration: {e}")

# --- 2. MAIN APP INTERFACE (Role-Based) ---
else:
    user_role = st.session_state.get('user_role', 'user') # Get the role
    user_name = st.session_state.get('user_name', 'user') # Get the name

    # --- Sidebar Navigation ---
    st.sidebar.title(f"Welcome, {user_name}!")
    st.sidebar.caption(f"Role: {user_role}")
    
    # Define available pages based on role
    available_pages = ["Chatbot"]
    if user_role == "student":
        available_pages.append("Grades") 
        available_pages.append("Schedules")
        available_pages.append("Instructor Schedules")
    if user_role in ["staff", "admin"]:
        available_pages.append("Course Management")
        available_pages.append("Student Data")
        available_pages.append("Reports")
        available_pages.append("Instructor Schedules")
    if user_role == "admin":
        available_pages.append("User Management")
        available_pages.append("Analytics")
        available_pages.append("Admin Settings")
        
    # Page selection in the sidebar
    page = st.sidebar.radio("Navigate", available_pages)
    
    st.sidebar.divider() # Adds a visual separator
    st.sidebar.button("Logout", on_click=logout_user)

    # --- Main Content Area (Conditional Rendering) ---
    
    token = f"Bearer {st.session_state.get('access_token')}"
    headers = {"Authorization": token}

    if page == "Chatbot":
        st.title("College AI Chatbot 🤖")
        
        # Display existing chat messages
        for chat in st.session_state.chat_history:
            with st.chat_message("user"):
                st.markdown(chat['user'])
            with st.chat_message("assistant"):
                st.markdown(chat['bot'])

        # Chat input at the bottom
        if prompt := st.chat_input("What would you like to know?"):
            # Add user message to history and display it
            st.session_state.chat_history.append({"user": prompt, "bot": "..."})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get bot response
            bot_response = get_chat_response(prompt)
            
            if bot_response:
                # Update the last bot message in history
                st.session_state.chat_history[-1]['bot'] = bot_response
                # Rerun to display the new message
                st.rerun()

    elif page == "Grades":
        st.title("📊 My Grades")
        try:
            response = requests.get(f"{BACKEND_URL}/grades", headers=headers)
            if response.status_code == 200:
                grades = response.json()
                if grades:
                    st.subheader("Your Current Grades")
                    display_data = [{"Course Name": g['course_name'], "Grade": g['grade']} for g in grades]
                    st.dataframe(display_data, use_container_width=0) # Use width=0 for container width
                else:
                    st.write("No grades found.")
            elif response.status_code == 403:
                 st.error("Only students can view grades.")
            else:
                 st.error(f"Failed to fetch grades: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching grades: {e}")


    elif page == "Schedules":
        st.title("🗓️ Course Schedules")
        try:
            response = requests.get(f"{BACKEND_URL}/schedules", headers=headers)
            if response.status_code == 200:
                schedules = response.json()
                if schedules:
                    st.subheader("Full Course Schedule")
                    display_data = [{
                        "Course Name": s['course_name'], 
                        "Day": s['day_of_week'], 
                        "Start Time": s['start_time'],
                        "End Time": s['end_time'],
                        "Location": s.get('location', 'N/A')
                    } for s in schedules]
                    st.dataframe(display_data, use_container_width=0)
                else:
                    st.write("No schedule information found.")
            else:
                 st.error(f"Failed to fetch schedules: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching schedules: {e}")

    elif page == "Instructor Schedules":
        st.title("👨‍🏫 Instructor Schedules")
        instructors = []
        try:
            courses_resp = requests.get(f"{BACKEND_URL}/courses", headers=headers)
            if courses_resp.status_code == 200:
                courses = courses_resp.json()
                instructors = sorted(list(set(c['instructor'] for c in courses))) 
            else:
                 st.error("Could not fetch instructor list.")
        except Exception as e:
            st.error(f"Error fetching instructors: {e}")

        if instructors:
            selected_instructor = st.selectbox("Select an Instructor", options=instructors)
            if selected_instructor:
                try:
                    encoded_instructor = urllib.parse.quote(selected_instructor)
                    schedule_resp = requests.get(f"{BACKEND_URL}/schedules/instructor/{encoded_instructor}", headers=headers)
                    if schedule_resp.status_code == 200:
                        instructor_schedule = schedule_resp.json()
                        if instructor_schedule:
                            st.subheader(f"Teaching Schedule for {selected_instructor}")
                            display_data = [{
                                "Course Name": s['course_name'], 
                                "Day": s['day_of_week'], 
                                "Start Time": s['start_time'],
                                "End Time": s['end_time'],
                                "Location": s.get('location', 'N/A')
                            } for s in instructor_schedule]
                            st.dataframe(display_data, use_container_width=0)
                        else:
                            st.write(f"{selected_instructor} has no scheduled classes found.")
                    else:
                        st.error(f"Failed to fetch schedule for {selected_instructor}: {schedule_resp.text}")
                except Exception as e:
                    st.error(f"An error occurred fetching the schedule: {e}")
        else:
             st.write("No instructors found to display schedules for.")

    elif page == "Course Management":
        st.title("📚 Course Management")
        st.write("Here you can view, add, edit, and delete courses.")

        with st.expander("➕ Add New Course"):
            with st.form("new_course_form", clear_on_submit=True):
                new_name = st.text_input("Course Name")
                new_desc = st.text_area("Description")
                new_instructor = st.text_input("Instructor")
                submitted_new = st.form_submit_button("Add Course")
                if submitted_new:
                    if not new_name or not new_desc or not new_instructor:
                        st.warning("Please fill out all fields.")
                    else:
                        new_course_data = {"name": new_name, "description": new_desc, "instructor": new_instructor}
                        try:
                            response = requests.post(f"{BACKEND_URL}/courses", json=new_course_data, headers=headers)
                            if response.status_code == 200:
                                st.success("Course added successfully!"); st.rerun()
                            else: st.error(f"Failed to add course: {response.text}")
                        except Exception as e: st.error(f"Error adding course: {e}")

        with st.expander("🎓 Add Grade for Student"):
             try:
                 students_resp = requests.get(f"{BACKEND_URL}/students", headers=headers)
                 courses_resp = requests.get(f"{BACKEND_URL}/courses", headers=headers)
                 if students_resp.status_code == 200 and courses_resp.status_code == 200:
                     students = students_resp.json(); courses = courses_resp.json()
                     student_options = {s['name']: s['id'] for s in students}
                     course_options = {c['name']: c['id'] for c in courses}
                     with st.form("add_grade_form", clear_on_submit=True):
                         selected_student_name = st.selectbox("Select Student", options=student_options.keys())
                         selected_course_name = st.selectbox("Select Course", options=course_options.keys())
                         grade_value = st.text_input("Enter Grade (e.g., A, B+, 85%)")
                         submitted_grade = st.form_submit_button("Add Grade")
                         if submitted_grade:
                             if not selected_student_name or not selected_course_name or not grade_value:
                                 st.warning("Please select student, course, and enter a grade.")
                             else:
                                 student_id = student_options[selected_student_name]
                                 course_id = course_options[selected_course_name]
                                 grade_data = {"student_id": student_id, "course_id": course_id, "grade": grade_value}
                                 try:
                                     response = requests.post(f"{BACKEND_URL}/grades", json=grade_data, headers=headers)
                                     if response.status_code == 200: st.success("Grade added successfully!")
                                     else: st.error(f"Failed to add grade: {response.text}")
                                 except Exception as e: st.error(f"Error adding grade: {e}")
                 else: st.error("Could not load students or courses for grade entry.")
             except Exception as e: st.error(f"Error loading data for grade form: {e}")

        with st.expander("🗓️ Add Course Schedule Entry"):
            try:
                courses_resp = requests.get(f"{BACKEND_URL}/courses", headers=headers)
                if courses_resp.status_code == 200:
                    courses = courses_resp.json()
                    course_options = {c['name']: c['id'] for c in courses}
                    with st.form("add_schedule_form", clear_on_submit=True):
                        selected_course_name = st.selectbox("Select Course for Schedule", options=course_options.keys(), key="sched_course")
                        day = st.selectbox("Day of Week", options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="sched_day")
                        start = st.text_input("Start Time (e.g., 10:00)")
                        end = st.text_input("End Time (e.g., 11:30)")
                        loc = st.text_input("Location (Optional)")
                        submitted_schedule = st.form_submit_button("Add Schedule Entry")
                        if submitted_schedule:
                            if not selected_course_name or not day or not start or not end:
                                st.warning("Please select course, day, start time, and end time.")
                            else:
                                course_id = course_options[selected_course_name]
                                schedule_data = {"course_id": course_id, "day_of_week": day, "start_time": start, "end_time": end, "location": loc if loc else None}
                                try:
                                    response = requests.post(f"{BACKEND_URL}/schedules", json=schedule_data, headers=headers)
                                    if response.status_code == 200: st.success("Schedule entry added successfully!")
                                    else: st.error(f"Failed to add schedule entry: {response.text}")
                                except Exception as e: st.error(f"Error adding schedule entry: {e}")
                else: st.error("Could not load courses for schedule entry.")
            except Exception as e: st.error(f"Error loading data for schedule form: {e}")

        st.divider()
        st.subheader("Existing Courses")
        try:
            response = requests.get(f"{BACKEND_URL}/courses", headers=headers)
            if response.status_code == 200:
                courses = response.json()
                if courses:
                    display_data = [{"id": c['id'], "name": c['name'], "description": c['description'], "instructor": c['instructor']} for c in courses]
                    cols = st.columns((1, 2, 3, 2, 1.5, 1.5))
                    column_headers = ["ID", "Name", "Description", "Instructor", "Edit", "Delete"]
                    for col, header_text in zip(cols, column_headers): col.write(f"**{header_text}**")
                    st.divider()
                    for course_data in display_data:
                        row_key = course_data['id']
                        cols = st.columns((1, 2, 3, 2, 1.5, 1.5))
                        cols[0].write(course_data['id'])
                        cols[1].write(course_data['name'])
                        cols[2].write(course_data['description'])
                        cols[3].write(course_data['instructor'])
                        with cols[4]:
                             with st.expander("✏️", expanded=False):
                                 with st.form(f"edit_form_{row_key}", clear_on_submit=True):
                                     st.write(f"Editing Course ID: {row_key}")
                                     edit_name = st.text_input("Name", value=course_data['name'], key=f"edit_name_{row_key}")
                                     edit_desc = st.text_area("Description", value=course_data['description'], key=f"edit_desc_{row_key}")
                                     edit_instructor = st.text_input("Instructor", value=course_data['instructor'], key=f"edit_inst_{row_key}")
                                     submitted_edit = st.form_submit_button("Update Course")
                                     if submitted_edit:
                                         updated_course_data = {"name": edit_name, "description": edit_desc, "instructor": edit_instructor}
                                         try:
                                             edit_response = requests.put(f"{BACKEND_URL}/courses/{row_key}", json=updated_course_data, headers=headers)
                                             if edit_response.status_code == 200: st.success(f"Course {row_key} updated."); st.rerun()
                                             else: st.error(f"Failed to update course: {edit_response.text}")
                                         except Exception as e: st.error(f"Error updating course: {e}")
                        if cols[5].button("🗑️", key=f"delete_{row_key}"):
                            try:
                                delete_response = requests.delete(f"{BACKEND_URL}/courses/{row_key}", headers=headers)
                                if delete_response.status_code == 200: st.success(f"Course {row_key} deleted."); st.rerun()
                                else: st.error(f"Failed to delete course: {delete_response.text}")
                            except Exception as e: st.error(f"Error deleting course: {e}")
                else: st.write("No courses found.")
            else: st.error(f"Failed to fetch courses: {response.text}")
        except Exception as e: st.error(f"An error occurred fetching courses: {e}")

    # (Inside the main 'else' block, after the 'Analytics' block)

    elif page == "Admin Settings":
        st.title("⚙️ Admin Settings")

        token = f"Bearer {st.session_state.get('access_token')}"
        headers = {"Authorization": token}

        st.subheader("Chatbot Prompt Customization")

        try:
            # Get the current prompt
            response_get = requests.get(f"{BACKEND_URL}/admin/prompt", headers=headers)

            if response_get.status_code == 200:
                current_prompt = response_get.json().get("prompt", "You are a helpful college chatbot.")

                with st.form("prompt_form"):
                    st.write("Edit the base system prompt for the AI chatbot. This defines its core personality and instructions.")
                    prompt_text = st.text_area("System Prompt", value=current_prompt, height=250)
                    submitted_prompt = st.form_submit_button("Save Prompt")

                    if submitted_prompt:
                        update_data = {"prompt": prompt_text}
                        try:
                            response_put = requests.put(f"{BACKEND_URL}/admin/prompt", json=update_data, headers=headers)
                            if response_put.status_code == 200:
                                st.success("System prompt updated successfully!")
                            else:
                                st.error(f"Failed to update prompt: {response_put.text}")
                        except Exception as e:
                            st.error(f"Error updating prompt: {e}")
            else:
                st.error(f"Failed to load current prompt: {response_get.text}")

        except Exception as e:
            st.error(f"An error occurred: {e}")

    # (Keep other elif blocks)
    # ...

    elif page == "Student Data":
        st.title("🧑‍🎓 Student Data Access")
        
        with st.expander("✅ Enroll Student in Course"):
            try:
                students_resp = requests.get(f"{BACKEND_URL}/students", headers=headers)
                courses_resp = requests.get(f"{BACKEND_URL}/courses", headers=headers)

                if students_resp.status_code == 200 and courses_resp.status_code == 200:
                    students = students_resp.json()
                    courses = courses_resp.json()
                    student_options = {s['name']: s['id'] for s in students}
                    course_options = {c['name']: c['id'] for c in courses}
                    with st.form("enroll_student_form", clear_on_submit=True):
                        selected_student_name = st.selectbox("Select Student to Enroll", options=student_options.keys())
                        selected_course_name = st.selectbox("Select Course", options=course_options.keys())
                        submitted_enroll = st.form_submit_button("Enroll Student")
                        if submitted_enroll:
                            if not selected_student_name or not selected_course_name:
                                st.warning("Please select a student and a course.")
                            else:
                                student_id = student_options[selected_student_name]
                                course_id = course_options[selected_course_name]
                                enrollment_data = {"student_id": student_id, "course_id": course_id}
                                try:
                                    response = requests.post(f"{BACKEND_URL}/enrollments", json=enrollment_data, headers=headers)
                                    if response.status_code == 200: st.success("Student enrolled successfully!")
                                    else: st.error(f"Failed to enroll student: {response.text}")
                                except Exception as e: st.error(f"Error enrolling student: {e}")
                else:
                     st.error("Could not load students or courses for enrollment form.")
            except Exception as e:
                 st.error(f"Error loading data for enrollment form: {e}")
        
        st.divider() 

        st.subheader("List of Students")
        try:
            response = requests.get(f"{BACKEND_URL}/students", headers=headers)
            if response.status_code == 200:
                students = response.json()
                if students:
                    display_data = [{"id": s['id'], "name": s['name'], "email": s['email']} for s in students]
                    st.dataframe(display_data, user_container_width=0) # Use width=0
                else:
                    st.write("No students found.")
            elif response.status_code == 403:
                 st.error("Access denied. Staff or Admin only.")
            else:
                 st.error(f"Failed to fetch student data: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching student data: {e}")

    elif page == "User Management":
        st.title("👥 User Management")
        st.write("Here you can view, create, and delete users.")

        with st.expander("➕ Create New User (Staff/Admin)"):
            with st.form("create_user_form", clear_on_submit=True):
                create_name = st.text_input("Full Name")
                create_email = st.text_input("Email")
                create_password = st.text_input("Password", type="password")
                create_role = st.selectbox("Role", ["staff", "admin", "student"], index=0) 
                submitted_create = st.form_submit_button("Create User")
                if submitted_create:
                    if not create_name or not create_email or not create_password:
                        st.warning("Please fill out all fields.")
                    else:
                        new_user_data = {"name": create_name, "email": create_email, "password": create_password, "role": create_role}
                        try:
                            response = requests.post(f"{BACKEND_URL}/register", json=new_user_data, headers=headers)
                            if response.status_code == 200:
                                st.success(f"User '{create_name}' created successfully!")
                                st.rerun()
                            else: st.error(f"Creation failed: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e: st.error(f"Error creating user: {e}")
        
        st.divider() 
        
        st.subheader("Current Users")
        try:
            response = requests.get(f"{BACKEND_URL}/users", headers=headers)
            if response.status_code == 200:
                users = response.json()
                display_data = [{"id": u['id'], "name": u['name'], "email": u['email'], "role": u['role']} for u in users]
                cols = st.columns((1, 2, 2, 1, 1))
                column_headers = ["ID", "Name", "Email", "Role", "Action"]
                for col, header_text in zip(cols, column_headers): col.write(f"**{header_text}**")
                st.divider() 
                for user_data in display_data:
                    row_key = user_data['id']
                    cols = st.columns((1, 2, 2, 1, 1))
                    cols[0].write(user_data['id'])
                    cols[1].write(user_data['name'])
                    cols[2].write(user_data['email'])
                    cols[3].write(user_data['role'])
                    if cols[4].button("Delete", key=f"delete_{row_key}"):
                        delete_response = requests.delete(f"{BACKEND_URL}/users/{user_data['id']}", headers=headers)
                        if delete_response.status_code == 200:
                            st.success(f"User {user_data['name']} deleted successfully."); st.rerun()
                        else: st.error(f"Failed to delete user: {delete_response.text}")
            elif response.status_code == 403: st.error("You do not have permission to view users.")
            else: st.error(f"Failed to fetch users: {response.text}")
        except Exception as e: st.error(f"An error occurred: {e}")

    elif page == "Reports":
        st.title("📊 Reports")
        st.subheader("Grade Distribution per Course")
        try:
            response = requests.get(f"{BACKEND_URL}/reports/grade-distribution", headers=headers)
            if response.status_code == 200:
                report_data = response.json()
                if report_data:
                    for course_name, grade_counts in report_data.items():
                        st.markdown(f"**{course_name}**")
                        if grade_counts:
                            grades_str = ", ".join([f"{grade}: {count}" for grade, count in sorted(grade_counts.items())])
                            st.write(grades_str)
                        else:
                            st.write("No grades recorded for this course.")
                        st.divider()
                else:
                    st.write("No grade data available to generate report.")
            elif response.status_code == 403:
                 st.error("Access denied. Staff or Admin only.")
            else:
                 st.error(f"Failed to fetch report data: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching the report: {e}")

    elif page == "Analytics":
        st.title("📈 Usage Analytics")
        try:
            response = requests.get(f"{BACKEND_URL}/analytics/usage", headers=headers)
            if response.status_code == 200:
                analytics_data = response.json()
                col1, col2, col3 = st.columns(3)
                col1.metric(label="Total Users", value=analytics_data.get("total_users", 0))
                col2.metric(label="Total Courses", value=analytics_data.get("total_courses", 0))
                col3.metric(label="Total Conversations", value=analytics_data.get("total_conversations", 0))
            else:
                 st.error(f"Failed to fetch basic analytics: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching basic analytics: {e}")

        st.divider()
        st.subheader("Chatbot Usage per Student")
        try:
            usage_response = requests.get(f"{BACKEND_URL}/analytics/conversations-per-student", headers=headers)
            if usage_response.status_code == 200:
                student_usage = usage_response.json()
                if student_usage:
                     display_data = [{"Name": s['name'], "Email": s['email'], "Messages Sent": s['message_count']} for s in student_usage]
                     st.dataframe(display_data, use_container_width=0) # Use width=0
                else:
                    st.write("No student conversation data found.")
            elif usage_response.status_code == 403:
                 st.error("Access denied. Admin only for usage details.")
            else:
                 st.error(f"Failed to fetch usage data: {usage_response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching usage analytics: {e}")


