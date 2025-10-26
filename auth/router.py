from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models.schemas import User, UserDisplay
import database
from . import utils, jwt

router = APIRouter()

@router.post("/register", response_model=UserDisplay)
def register_user(user: User):
    """Registers a new user in the database."""
    conn = database.get_db_connection()

    # Check if user email already exists
    db_user = conn.execute('SELECT * FROM users WHERE email = ?', (user.email,)).fetchone()
    if db_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password and create the user
    hashed_password = utils.get_password_hash(user.password)

    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
        (user.name, user.email, hashed_password, user.role)
    )
    new_user_id = cursor.lastrowid
    conn.commit()

    # Get the newly created user to return it
    new_user = conn.execute('SELECT * FROM users WHERE id = ?', (new_user_id,)).fetchone()
    conn.close()

    return dict(new_user)

@router.post("/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Logs in a user and returns an access token."""
    conn = database.get_db_connection()
    db_user = conn.execute('SELECT * FROM users WHERE email = ?', (form_data.username,)).fetchone()
    conn.close()

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