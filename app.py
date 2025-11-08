import streamlit as st
import requests
import urllib.parse # For instructor schedules

# --- Configuration ---
# Make sure this is your public Render URL
BACKEND_URL = "https://ai-college-chatbot-backend.onrender.com" 

# --- NEW STYLING (Inject custom CSS) ---
st.markdown("""
<style>
/* Center the main content block for the login page */
div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"]:first-child {
    max-width: 550px; /* Set a max width for the forms */
    margin: 0 auto;   /* Center the block */
}

/* Style the form containers as cards */
div[data-testid="stForm"] {
    border: 1px solid #e6e6e6;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    background-color: #ffffff;
    margin-bottom: 2rem; /* Add space between forms */
}

/* Style the form buttons */
div[data-testid="stForm"] .stButton > button {
    width: 100%;
    border: none;
    border-radius: 5px;
    padding: 10px 0;
    font-weight: bold;
    color: white;
    background-color: #1c88e5; /* A fresh blue */
    transition: background-color 0.3s ease;
}

div[data-testid="stForm"] .stButton > button:hover {
    background-color: #005eb8;
}

/* Center the title and add a nice font */
h1 {
    text-align: center;
    font-family: 'Arial', sans-serif;
    color: #333;
}
h2 {
    text-align: center;
    font-family: 'Arial', sans-serif;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# In: app.py
# REPLACE this entire function

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
            headers = {"Authorization": token} 

            # --- Get user details ---
            user_details_response = requests.get(
                f"{BACKEND_URL}/users/me", 
                headers=headers 
            )
            if user_details_response.status_code == 200:
                user_details = user_details_response.json()
                st.session_state['user_role'] = user_details.get('role')
                st.session_state['user_name'] = user_details.get('name', 'user')
                st.session_state['user_year_of_study'] = user_details.get('year_of_study') 
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
                st.session_state['chat_history'] = []

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

st.set_page_config(page_title="Brindavan Group of Institutions",page_icon="🎓", layout="wide") # Use wide layout

# Initialize session state if it doesn't exist
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# --- 1. LOGIN PAGE (MODIFIED) ---
if not st.session_state['logged_in']:
    
    st.title("🎓 Hello, from your personal college guide")
    
    # Placeholder for a college banner image
    st.image("banner.png", use_container_width=True)
    st.write("") # Add some space
    
    # Use columns to center the forms in a narrower block
    col1, col_main, col3 = st.columns([1, 1.5, 1]) # 1:1.5:1 ratio centers the middle column
    
    with col_main:
        # Login Form Card
        st.subheader("Please log in")
        with st.form("login_form"):
            username = st.text_input("Email (Username)")
            password = st.text_input("Password", type="password")
            submitted_login = st.form_submit_button("Login")
            
            if submitted_login:
                login_user(username, password)

        # Registration Form Card
        st.subheader("New Student? Register Here")
        with st.form("register_form", clear_on_submit=True):
            reg_name = st.text_input("Full Name")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Choose Password", type="password")
            reg_year = st.selectbox("Year of Study", [1, 2, 3, 4])
            reg_role = "admin" # Default registration role
            submitted_register = st.form_submit_button("Register")

            if submitted_register:
                if not reg_name or not reg_email or not reg_password:
                    st.warning("Please fill out all registration fields.")
                else:
                    user_data = {
                        "name": reg_name,
                        "email": reg_email,
                        "password": reg_password,
                        "role": reg_role, 
                        "year_of_study": reg_year
                    }
                    try:
                        response = requests.post(f"{BACKEND_URL}/register", json=user_data)
                        if response.status_code == 200: 
                            st.success("Registration successful! Please log in.")
                        elif response.status_code == 400: 
                            st.error(f"Registration failed: {response.json().get('detail', 'Unknown error')}")
                        else:
                            st.error(f"Registration failed with code {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"Error during registration: {e}")

# --- 2. MAIN APP INTERFACE (Role-Based) ---
# In: app.py
# REPLACE the entire 'else' block (from line ~117 to the end)

# --- 2. MAIN APP INTERFACE (Role-Based) ---
else:
    user_role = st.session_state.get('user_role', 'user') 
    user_name = st.session_state.get('user_name', 'user')
    user_year = st.session_state.get('user_year_of_study')

    # --- Sidebar Navigation ---
    st.sidebar.title(f"Welcome, {user_name}!")
    st.sidebar.caption(f"Role: {user_role}")
    if user_role == 'student' and user_year:
        st.sidebar.caption(f"Year: {user_year}")

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
        
    page = st.sidebar.radio("Navigate", available_pages)
    
    # --- Year Filter for Staff/Admin ---
    year_filter = None
    if user_role in ["staff", "admin"] and page not in ["Chatbot", "Admin Settings"]:
        year_options = ["All", 1, 2, 3, 4]
        year_filter = st.sidebar.selectbox("Filter by Year", options=year_options)

    st.sidebar.divider() 
    st.sidebar.button("Logout", on_click=logout_user)

    # --- Main Content Area (Conditional Rendering) ---
    
    token = f"Bearer {st.session_state.get('access_token')}"
    headers = {"Authorization": token}
    
    # Prepare API query params
    params = {}
    if user_role == 'student' and user_year:
        params['year'] = user_year # Students auto-filter for their own year
    elif year_filter and year_filter != "All":
        params['year'] = year_filter # Staff/Admin use the filter

    if page == "Chatbot":
        # ... (Chatbot code remains the same, no changes needed) ...
        st.title("College AI Chatbot 🤖")
        for chat in st.session_state.chat_history:
            with st.chat_message("user"): st.markdown(chat['user'])
            with st.chat_message("assistant"): st.markdown(chat['bot'])
        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.chat_history.append({"user": prompt, "bot": "..."})
            with st.chat_message("user"): st.markdown(prompt)
            bot_response = get_chat_response(prompt)
            if bot_response:
                st.session_state.chat_history[-1]['bot'] = bot_response
                st.rerun()

    elif page == "Grades":
        st.title("📊 My Grades")
        try:
            # Student's view is auto-filtered by their year
            response = requests.get(f"{BACKEND_URL}/grades", headers=headers, params=params) 
            if response.status_code == 200:
                marks_list = response.json()
                if marks_list:
                    st.subheader(f"Your Marks for Year {user_year}")
                    pass_mark = 26.25
                    for item in marks_list:
                        st.markdown(f"#### {item['course_name']}")
                        total = item['total_marks']
                        status = item['status']
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("Internal 1", f"{item['internal_1']} / 25")
                        col2.metric("Internal 2", f"{item['internal_2']} / 25")
                        col3.metric("Internal 3", f"{item['internal_3']} / 25")
                        col4.metric("Total", f"{total} / 75")
                        if status == "Pass": col5.success(f"Status: {status}")
                        else: col5.error(f"Status: {status}")
                        difference = total - pass_mark
                        if status == "Pass": st.caption(f"You are {difference:.2f} marks above the passing mark of {pass_mark}.")
                        else: st.caption(f"You are {abs(difference):.2f} marks below the passing mark of {pass_mark}.")
                        st.divider()
                else:
                    st.write(f"No marks found for Year {user_year}.")
            else:
                 st.error(f"Failed to fetch grades: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching grades: {e}")

    elif page == "Schedules":
        st.title("🗓️ Course Schedules")
        try:
            # Student's view is auto-filtered by their year
            response = requests.get(f"{BACKEND_URL}/schedules", headers=headers, params=params)
            if response.status_code == 200:
                schedules = response.json()
                if schedules:
                    st.subheader(f"Full Course Schedule for Year {user_year}")
                    display_data = [{"Course Name": s['course_name'], "Day": s['day_of_week'], "Start Time": s['start_time'], "End Time": s['end_time'], "Location": s.get('location', 'N/A')} for s in schedules]
                    st.dataframe(display_data, use_container_width=True)
                else:
                    st.write(f"No schedule information found for Year {user_year}.")
            else:
                 st.error(f"Failed to fetch schedules: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching schedules: {e}")

    elif page == "Instructor Schedules":
        st.title("👨‍🏫 Instructor Schedules")
        instructors = []
        try:
            # Pass the year filter to get relevant instructors
            courses_resp = requests.get(f"{BACKEND_URL}/courses", headers=headers, params=params)
            if courses_resp.status_code == 200:
                courses = courses_resp.json()
                instructors = sorted(list(set(c['instructor'] for c in courses))) 
            else:
                 st.error(f"Could not fetch instructor list for year {params.get('year', 'All')}.")
        except Exception as e:
            st.error(f"Error fetching instructors: {e}")

        if instructors:
            selected_instructor = st.selectbox("Select an Instructor", options=instructors)
            if selected_instructor:
                try:
                    encoded_instructor = urllib.parse.quote(selected_instructor)
                    # Pass the year filter to the instructor schedule endpoint
                    schedule_resp = requests.get(f"{BACKEND_URL}/schedules/instructor/{encoded_instructor}", headers=headers, params=params)
                    if schedule_resp.status_code == 200:
                        instructor_schedule = schedule_resp.json()
                        if instructor_schedule:
                            st.subheader(f"Teaching Schedule for {selected_instructor}")
                            display_data = [{"Course Name": s['course_name'], "Day": s['day_of_week'], "Start Time": s['start_time'], "End Time": s['end_time'], "Location": s.get('location', 'N/A')} for s in instructor_schedule]
                            st.dataframe(display_data, use_container_width=True)
                        else:
                            st.write(f"{selected_instructor} has no scheduled classes found {f'for Year {year_filter}' if year_filter and year_filter != 'All' else ''}.")
                    else:
                        st.error(f"Failed to fetch schedule for {selected_instructor}: {schedule_resp.text}")
                except Exception as e:
                    st.error(f"An error occurred fetching the schedule: {e}")
        else:
             st.write(f"No instructors found {f'for Year {year_filter}' if year_filter and year_filter != 'All' else ''}.")

    elif page == "Course Management":
        st.title("📚 Course Management")
        st.write("Here you can view, add, edit, and delete courses.")
        
        # --- Forms for adding data (no change needed here) ---
        with st.expander("➕ Add New Course"):
            # ... (Your existing Add New Course form code) ...
            # Make sure the form includes the 'year_of_study' selectbox
            pass
        with st.expander("✍️ Enter/Update Internal Marks"):
            # ... (Your existing Enter/Update Marks form code) ...
            pass
        with st.expander("🗓️ Add Course Schedule Entry"):
            # ... (Your existing Add Schedule Entry form code) ...
            pass

        st.divider()
        st.subheader(f"Existing Courses (Year: {year_filter if year_filter else 'All'})")
        try:
            # Pass the year filter params to the API call
            response = requests.get(f"{BACKEND_URL}/courses", headers=headers, params=params)
            if response.status_code == 200:
                courses = response.json()
                if courses:
                    # ... (Your existing code to display courses, edit, and delete) ...
                    # This part remains the same, it just shows the filtered list
                    display_data = [{"id": c['id'], "name": c['name'], "description": c['description'], "instructor": c['instructor'], "year": c['year_of_study']} for c in courses]
                    cols = st.columns((0.5, 2, 3, 2, 1, 1, 1)) # Added year
                    column_headers = ["ID", "Name", "Description", "Instructor", "Year", "Edit", "Delete"]
                    for col, header_text in zip(cols, column_headers): col.write(f"**{header_text}**")
                    st.divider()
                    for course_data in display_data:
                        row_key = course_data['id']
                        cols = st.columns((0.5, 2, 3, 2, 1, 1, 1))
                        cols[0].write(course_data['id'])
                        cols[1].write(course_data['name'])
                        cols[2].write(course_data['description'])
                        cols[3].write(course_data['instructor'])
                        cols[4].write(course_data['year'])
                        with cols[5]:
                             with st.expander("✏️", expanded=False):
                                 with st.form(f"edit_form_{row_key}", clear_on_submit=True):
                                     # ... (your existing edit form code) ...
                                     pass
                        if cols[6].button("🗑️", key=f"delete_{row_key}"):
                            # ... (your existing delete button code) ...
                            pass
                else:
                    st.write(f"No courses found for Year {year_filter if year_filter else 'All'}.")
            else: st.error(f"Failed to fetch courses: {response.text}")
        except Exception as e: st.error(f"An error occurred fetching courses: {e}")

    elif page == "Student Data":
        st.title("🧑‍🎓 Student Data Access")
        
        with st.expander("✅ Enroll Student in Course"):
            # ... (Your existing Enroll Student form code, no changes needed) ...
            pass
        
        st.divider() 
        st.subheader(f"List of Students (Year: {year_filter if year_filter else 'All'})")
        try:
            # Pass the year filter params to the API call
            response = requests.get(f"{BACKEND_URL}/students", headers=headers, params=params)
            if response.status_code == 200:
                students = response.json()
                if students:
                    # Add AI Summary logic
                    display_data = [{"id": s['id'], "name": s['name'], "email": s['email'], "year": s.get('year_of_study', 'N/A')} for s in students]
                    
                    # Header
                    st.markdown("---")
                    cols_header = st.columns([2, 3, 1, 2])
                    cols_header[0].write("**Name (ID)**")
                    cols_header[1].write("**Email**")
                    cols_header[2].write("**Year**")
                    cols_header[3].write("**AI Action**")
                    st.markdown("---")
                    
                    for s in display_data:
                        student_id = s['id']
                        col1, col2, col3, col4 = st.columns([2, 3, 1, 2])
                        with col1:
                            st.markdown(f"**{s['name']}**")
                            st.caption(f"ID: {student_id}")
                        with col2: st.write(s['email'])
                        with col3: st.write(s['year'])
                        with col4:
                            if st.button("Generate AI Summary", key=f"analyze_{student_id}"):
                                with st.spinner(f"Analyzing {s['name']}..."):
                                    try:
                                        summary_resp = requests.get(f"{BACKEND_URL}/reports/student-summary/{student_id}", headers=headers)
                                        if summary_resp.status_code == 200:
                                            st.session_state[f"summary_for_{student_id}"] = summary_resp.json().get("summary")
                                        else: st.error(f"Failed to get summary: {summary_resp.text}")
                                    except Exception as e: st.error(f"Error during analysis: {e}")
                        
                        if f"summary_for_{student_id}" in st.session_state:
                            st.info(st.session_state[f"summary_for_{student_id}"])
                        st.markdown("---") # Divider
                else:
                    st.write(f"No students found for Year {year_filter if year_filter else 'All'}.")
            else:
                 st.error(f"Failed to fetch student data: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching student data: {e}")

    elif page == "User Management":
        st.title("👥 User Management")
        st.write("Here you can view, create, and delete users.")

        with st.expander("➕ Create New User (Staff/Admin)"):
            # ... (Your existing Create User form code, no changes needed) ...
            pass
        
        st.divider() 
        st.subheader("Current Users")
        try:
            # Note: /users endpoint does not have a year filter, it shows all users (admins, staff)
            response = requests.get(f"{BACKEND_URL}/users", headers=headers)
            if response.status_code == 200:
                users = response.json()
                display_data = [{"id": u['id'], "name": u['name'], "email": u['email'], "role": u['role'], "year": u.get('year_of_study', 'N/A')} for u in users]
                cols = st.columns((0.5, 2, 2, 1, 1, 1)) # Added Year
                column_headers = ["ID", "Name", "Email", "Role", "Year", "Action"]
                for col, header_text in zip(cols, column_headers): col.write(f"**{header_text}**")
                st.divider() 
                for user_data in display_data:
                    row_key = user_data['id']
                    cols = st.columns((0.5, 2, 2, 1, 1, 1))
                    cols[0].write(user_data['id'])
                    cols[1].write(user_data['name'])
                    cols[2].write(user_data['email'])
                    cols[3].write(user_data['role'])
                    cols[4].write(user_data['year'])
                    if cols[5].button("Delete", key=f"delete_{row_key}"):
                        # ... (your existing delete button code) ...
                        pass
            else: st.error(f"Failed to fetch users: {response.text}")
        except Exception as e: st.error(f"An error occurred: {e}")

    elif page == "Reports":
        st.title("📊 Reports")
        st.subheader(f"Grade Distribution per Course (Year: {year_filter if year_filter else 'All'})")
        try:
            # Pass the year filter params to the API call
            response = requests.get(f"{BACKEND_URL}/reports/grade-distribution", headers=headers, params=params)
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
                    st.write(f"No grade data available to generate report for Year {year_filter if year_filter else 'All'}.")
            else:
                 st.error(f"Failed to fetch report data: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching the report: {e}")

    elif page == "Analytics":
        st.title("📈 Usage Analytics")
        try:
            # Analytics also needs to be filtered by year
            response = requests.get(f"{BACKEND_URL}/analytics/usage", headers=headers, params=params)
            if response.status_code == 200:
                analytics_data = response.json()
                st.subheader(f"Overall Stats (Year: {year_filter if year_filter else 'All'})")
                col1, col2, col3 = st.columns(3)
                col1.metric(label="Total Users (Students in Year)", value=analytics_data.get("total_users", 0))
                col2.metric(label="Total Courses (in Year)", value=analytics_data.get("total_courses", 0))
                col3.metric(label="Total Conversations (from Students in Year)", value=analytics_data.get("total_conversations", 0))
            else:
                 st.error(f"Failed to fetch basic analytics: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching basic analytics: {e}")

        st.divider()
        st.subheader(f"Chatbot Usage per Student (Year: {year_filter if year_filter else 'All'})")
        try:
            # Pass the year filter params to the API call
            usage_response = requests.get(f"{BACKEND_URL}/analytics/conversations-per-student", headers=headers, params=params)
            if usage_response.status_code == 200:
                student_usage = usage_response.json()
                if student_usage:
                     display_data = [{"Name": s['name'], "Email": s['email'], "Messages Sent": s['message_count']} for s in student_usage]
                     st.dataframe(display_data, use_container_width=True)
                else:
                    st.write(f"No student conversation data found for Year {year_filter if year_filter else 'All'}.")
            else:
                 st.error(f"Failed to fetch usage data: {usage_response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching usage analytics: {e}")

    elif page == "Admin Settings":
        # ... (Admin Settings code remains the same, no changes needed) ...
        st.title("⚙️ Admin Settings")
        try:
            response_get = requests.get(f"{BACKEND_URL}/admin/prompt", headers=headers)
            if response_get.status_code == 200:
                current_prompt = response_get.json().get("prompt", "You are a helpful college chatbot.")
                with st.form("prompt_form"):
                    st.write("Edit the base system prompt for the AI chatbot.")
                    prompt_text = st.text_area("System Prompt", value=current_prompt, height=250)
                    submitted_prompt = st.form_submit_button("Save Prompt")
                    if submitted_prompt:
                        update_data = {"prompt": prompt_text}
                        try:
                            response_put = requests.put(f"{BACKEND_URL}/admin/prompt", json=update_data, headers=headers)
                            if response_put.status_code == 200: st.success("System prompt updated!")
                            else: st.error(f"Failed to update prompt: {response_put.text}")
                        except Exception as e: st.error(f"Error updating prompt: {e}")
            else: st.error(f"Failed to load current prompt: {response_get.text}")
        except Exception as e: st.error(f"An error occurred: {e}")