from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models.schemas import User, UserDisplay
import database
from . import utils, jwt

router = APIRouter()

@router.post("/register", response_model=UserDisplay)
def register_user(user: User):
    """Registers a new user in the database."""
    conn = None # Initialize conn to None
    cursor = None # Initialize cursor to None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor() # Create a cursor

        # Check if user email already exists using the cursor
        cursor.execute('SELECT * FROM users WHERE email = %s', (user.email,)) # Use %s for psycopg2 placeholders
        db_user = cursor.fetchone()

        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash the password
        hashed_password = utils.get_password_hash(user.password)

        # Insert the new user using the cursor and RETURNING id
        cursor.execute(
            'INSERT INTO users (name, email, password, role, year_of_study) VALUES (%s, %s, %s, %s, %s) RETURNING id',(user.name, user.email, hashed_password, user.role, user.year_of_study))
        new_user_id_row = cursor.fetchone() # Fetch the returned ID row
        if not new_user_id_row:
             raise HTTPException(status_code=500, detail="Failed to create user and get ID.")
        new_user_id = new_user_id_row['id'] # Get ID from the row

        conn.commit() # Commit the transaction

        # Get the newly created user to return it
        cursor.execute('SELECT id, name, email, role FROM users WHERE id = %s', (new_user_id,))
        new_user = cursor.fetchone()

        if not new_user:
             raise HTTPException(status_code=404, detail="Newly created user not found.")

        return new_user # RealDictCursor already returns a dict-like object

    except HTTPException: # Re-raise HTTP exceptions
         raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"Database error during registration: {error}")
        if conn:
            conn.rollback() # Roll back changes on error
        raise HTTPException(status_code=500, detail="Database error during registration.")
    finally:
        # Ensure cursor and connection are closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.post("/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Logs in a user and returns an access token."""
    conn = None
    cursor = None
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()

        # Fetch user by email using cursor
        cursor.execute('SELECT * FROM users WHERE email = %s', (form_data.username,))
        db_user = cursor.fetchone()

        # Check if user exists and password is correct
        if not db_user or not utils.verify_password(form_data.password, db_user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create a JWT token
        access_token = jwt.create_access_token(
            data={"sub": db_user['email'], "role": db_user['role']}
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except (Exception, database.psycopg2.DatabaseError) as error:
        print(f"Database error during login: {error}")
        # No rollback needed for SELECT
        raise HTTPException(status_code=500, detail="Database error during login.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()