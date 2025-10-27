import streamlit as st
import requests

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Your FastAPI server URL

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
                st.session_state['user_role'] = user_details_response.json().get('role')
            else:
                print(f"Error fetching user details: {user_details_response.status_code}")
                st.session_state['user_role'] = 'user' 

            # --- ADD THIS BLOCK: Fetch chat history ---
            history_response = requests.get(
                f"{BACKEND_URL}/chat/history",
                headers=headers 
            )
            if history_response.status_code == 200:
                # Store history correctly for the chat display
                history_data = history_response.json()
                st.session_state['chat_history'] = [{"user": row['message'], "bot": row['response']} for row in history_data]
            else:
                print(f"Error fetching chat history: {history_response.status_code}")
                st.session_state['chat_history'] = [] # Start fresh if history fails
            # --- END OF NEW BLOCK ---

            st.rerun() 
        else:
            st.error("Invalid username or password")
    except requests.ConnectionError:
        st.error("Failed to connect to the backend. Is it running?")
    except Exception as e:
        st.error(f"An error occurred: {e}")

def logout_user():
    """Logs out the user by clearing the session state."""
    st.session_state['logged_in'] = False
    st.session_state.pop('access_token', None)
    st.session_state.pop('user_role', None)
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
    st.subheader("Please log in to continue")

    with st.form("login_form"):
        username = st.text_input("Email (Username)")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            login_user(username, password)

# --- 2. MAIN APP INTERFACE (Role-Based) ---
else:
    user_role = st.session_state.get('user_role', 'user') # Get the role

    # --- Sidebar Navigation ---
    st.sidebar.title(f"Welcome, {user_role}!")
    
    # Define available pages based on role
    available_pages = ["Chatbot"]
    if user_role == "student":
        available_pages.append("Grades")
        available_pages.append("Schedules")
    if user_role in ["staff", "admin"]:
        available_pages.append("Course Management")
        available_pages.append("Student Data")
    if user_role == "admin":
        available_pages.append("User Management")
        
    # Page selection in the sidebar
    page = st.sidebar.radio("Navigate", available_pages)
    
    st.sidebar.divider() # Adds a visual separator
    st.sidebar.button("Logout", on_click=logout_user)

    # --- Main Content Area (Conditional Rendering) ---
    
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
    # (Inside the main 'else' block, after the 'if page == "Chatbot":' block)

    elif page == "Grades":
        st.title("📊 My Grades")
        
        # Get the authentication token from session state
        token = f"Bearer {st.session_state.get('access_token')}"
        headers = {"Authorization": token}
        try:
            # Call the backend API endpoint to get grades
            response = requests.get(f"{BACKEND_URL}/grades", headers=headers)
            
            # --- Start Debug Prints ---
            print(f"DEBUG: Grades API response status: {response.status_code}") 
            try:
                # Try to print the JSON response if successful
                print(f"DEBUG: Grades API response JSON: {response.json()}") 
            except requests.exceptions.JSONDecodeError:
                # If response is not JSON (e.g., an error), print the raw text
                print(f"DEBUG: Grades API response text: {response.text}") 
            # --- End Debug Prints ---
                
            # Check if the API call was successful
            if response.status_code == 200:
                grades = response.json() # Get the list of grades
                if grades:
                    st.subheader("Your Current Grades")
                    # Prepare data for a clean table display
                    # Ensure keys match what the API returns ('course_name', 'grade')
                    display_data = [{"Course Name": g['course_name'], "Grade": g['grade']} for g in grades]
                    # Display the data in a table that fills the width
                    st.dataframe(display_data, use_container_width=True) 
                else:
                    # Show message if no grades are found
                    st.write("No grades found.")
            elif response.status_code == 403:
                # Handle case where non-student tries to access
                st.error("Only students can view grades.")
            else:
                # Show error if API call failed for other reasons
                st.error(f"Failed to fetch grades: {response.text}")
                
        except Exception as e:
            # Catch any other errors during the process
            st.error(f"An error occurred fetching grades: {e}")

    # (Inside the main 'else' block, after the 'Grades' block)

    elif page == "Schedules":
        st.title("🗓️ Course Schedules")

        token = f"Bearer {st.session_state.get('access_token')}"
        headers = {"Authorization": token}

        try:
            response = requests.get(f"{BACKEND_URL}/schedules", headers=headers)

            if response.status_code == 200:
                schedules = response.json()
                if schedules:
                    st.subheader("Full Course Schedule")
                    # Prepare data for display
                    display_data = [{
                        "Course Name": s['course_name'], 
                        "Day": s['day_of_week'], 
                        "Start Time": s['start_time'],
                        "End Time": s['end_time'],
                        "Location": s.get('location', 'N/A') # Use .get for optional fields
                    } for s in schedules]
                    st.dataframe(display_data, use_container_width=True) # Display in a table
                else:
                    st.write("No schedule information found.")
            else:
                st.error(f"Failed to fetch schedules: {response.text}")

        except Exception as e:
            st.error(f"An error occurred fetching schedules: {e}")



    elif page == "Student Data":
        st.title("🧑‍🎓 Student Data Access")

        token = f"Bearer {st.session_state.get('access_token')}"
        headers = {"Authorization": token}

        try:
            response = requests.get(f"{BACKEND_URL}/students", headers=headers)

            if response.status_code == 200:
                students = response.json()
                if students:
                    st.subheader("List of Students")
                    # Prepare data for display
                    display_data = [{"id": s['id'], "name": s['name'], "email": s['email']} for s in students]
                    st.dataframe(display_data, use_container_width=True)
                else:
                    st.write("No students found.")
            elif response.status_code == 403:
                st.error("Access denied. Staff or Admin only.")
            else:
                st.error(f"Failed to fetch student data: {response.text}")

        except Exception as e:
            st.error(f"An error occurred fetching student data: {e}")

    elif page == "Course Management":
        st.title("📚 Course Management")
        st.write("Here you can view, add, edit, and delete courses.")

        token = f"Bearer {st.session_state.get('access_token')}"
        headers = {"Authorization": token}

        # --- Section to Add a New Course ---
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
                        new_course_data = {
                            "name": new_name,
                            "description": new_desc,
                            "instructor": new_instructor
                        }
                        try:
                            response = requests.post(f"{BACKEND_URL}/courses", json=new_course_data, headers=headers)
                            if response.status_code == 200:
                                st.success("Course added successfully!")
                                st.rerun() # Rerun to refresh the list immediately
                            elif response.status_code == 403:
                                st.error("Permission denied.")
                            else:
                                st.error(f"Failed to add course: {response.text}")
                        except Exception as e:
                            st.error(f"Error adding course: {e}")

        st.divider()

        # --- Section to Display Existing Courses ---
        st.subheader("Existing Courses")
        try:
            response = requests.get(f"{BACKEND_URL}/courses", headers=headers)
            if response.status_code == 200:
                courses = response.json()
                if courses:
                    # Prepare data for display
                    display_data = [{"id": c['id'], "name": c['name'], "description": c['description'], "instructor": c['instructor']} for c in courses]

                    # Header row
                    cols = st.columns((1, 2, 3, 2, 1.5, 1.5)) # ID, Name, Desc, Instructor, Edit, Delete
                    column_headers = ["ID", "Name", "Description", "Instructor", "Edit", "Delete"]
                    for col, header_text in zip(cols, column_headers):
                        col.write(f"**{header_text}**")
                    st.divider()

                    # Data rows
                    for course_data in display_data:
                        row_key = course_data['id']
                        cols = st.columns((1, 2, 3, 2, 1.5, 1.5))

                        # Display course info
                        cols[0].write(course_data['id'])
                        cols[1].write(course_data['name'])
                        cols[2].write(course_data['description'])
                        cols[3].write(course_data['instructor'])

                        # --- Edit Button and Form ---
                        with cols[4]:
                            # Use an expander for the edit form, triggered by a button if needed
                            # Or directly place a button that might toggle visibility or navigate
                            # For simplicity, we'll put the form in an expander per row
                            with st.expander("✏️", expanded=False):
                                with st.form(f"edit_form_{row_key}", clear_on_submit=True):
                                    st.write(f"Editing Course ID: {row_key}")
                                    edit_name = st.text_input("Name", value=course_data['name'], key=f"edit_name_{row_key}")
                                    edit_desc = st.text_area("Description", value=course_data['description'], key=f"edit_desc_{row_key}")
                                    edit_instructor = st.text_input("Instructor", value=course_data['instructor'], key=f"edit_inst_{row_key}")
                                    submitted_edit = st.form_submit_button("Update Course")

                                    if submitted_edit:
                                        updated_course_data = {
                                            "name": edit_name,
                                            "description": edit_desc,
                                            "instructor": edit_instructor
                                        }
                                        try:
                                            edit_response = requests.put(f"{BACKEND_URL}/courses/{row_key}", json=updated_course_data, headers=headers)
                                            if edit_response.status_code == 200:
                                                st.success(f"Course {row_key} updated successfully.")
                                                st.rerun() # Refresh list
                                            elif edit_response.status_code == 403:
                                                st.error("Permission denied.")
                                            elif edit_response.status_code == 404:
                                                st.error("Course not found (might have been deleted).")
                                            else:
                                                st.error(f"Failed to update course: {edit_response.text}")
                                        except Exception as e:
                                            st.error(f"Error updating course: {e}")


                        # --- Delete Button ---
                        if cols[5].button("🗑️", key=f"delete_{row_key}"):
                            try:
                                delete_response = requests.delete(f"{BACKEND_URL}/courses/{row_key}", headers=headers)
                                if delete_response.status_code == 200:
                                    st.success(f"Course {row_key} deleted successfully.")
                                    st.rerun() # Refresh list
                                elif delete_response.status_code == 403:
                                    st.error("Permission denied.")
                                elif delete_response.status_code == 404:
                                    st.error("Course not found (might have already been deleted).")
                                else:
                                    st.error(f"Failed to delete course: {delete_response.text}")
                            except Exception as e:
                                st.error(f"Error deleting course: {e}")

                else: # No courses found
                    st.write("No courses found.")
            elif response.status_code == 403:
                st.error("You do not have permission to view courses.")
            else:
                st.error(f"Failed to fetch courses: {response.text}")
        except Exception as e:
            st.error(f"An error occurred fetching or displaying courses: {e}")

    elif page == "User Management":
        st.title("👥 User Management")
        st.write("Here you can view and delete users.")

        token = f"Bearer {st.session_state.get('access_token')}"
        headers = {"Authorization": token}

        try:
            # --- Fetch users from backend ---
            response = requests.get(f"{BACKEND_URL}/users", headers=headers)

            if response.status_code == 200:
                users = response.json()

                # --- Display users in a more structured way ---
                st.subheader("Current Users")

                # Prepare data for display (exclude passwords if they were sent)
                display_data = [{"id": u['id'], "name": u['name'], "email": u['email'], "role": u['role']} for u in users]

                # Use st.columns for layout
                cols = st.columns((1, 2, 2, 1, 1)) # Adjust column widths as needed
                column_headers = ["ID", "Name", "Email", "Role", "Action"]
                for col, header_text in zip(cols, column_headers):
                    col.write(f"**{header_text}**") # Make headers bold

                st.divider() # Add a line separator

                for user_data in display_data:
                    # Create a unique key for the button
                    row_key = user_data['id']
                    cols = st.columns((1, 2, 2, 1, 1))
                    
                    # Display user data WITHOUT the key argument
                    cols[0].write(user_data['id'])
                    cols[1].write(user_data['name'])
                    cols[2].write(user_data['email'])
                    cols[3].write(user_data['role'])

                    # --- Delete button (NEEDS the key) ---
                    if cols[4].button("Delete", key=f"delete_{row_key}"):
                        delete_response = requests.delete(f"{BACKEND_URL}/users/{user_data['id']}", headers=headers)
                        if delete_response.status_code == 200:
                            st.success(f"User {user_data['name']} deleted successfully.")
                            st.rerun() # Refresh the page
                        else:
                            st.error(f"Failed to delete user: {delete_response.text}")

            elif response.status_code == 403: # Forbidden
                st.error("You do not have permission to view users.")
            else:
                st.error(f"Failed to fetch users: {response.text}")

        except Exception as e:
            st.error(f"An error occurred: {e}")