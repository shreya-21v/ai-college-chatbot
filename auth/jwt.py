from jose import JWTError, jwt
from decouple import config
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List
import database

# Load secrets from your .env file
JWT_SECRET = config('JWT_SECRET')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# This tells FastAPI where to check for the token (in the "Authorization" header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict):
    """Creates a new JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    """Checks if a token is valid and returns its data (payload)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

# This is a dependency that your API routes will use
# to get the currently logged-in user
# REPLACE your old get_current_user function with this new one
# REPLACE your old get_current_user function with this new one
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token, credentials_exception)
    
    email: str = payload.get("sub")
    
    # Get user details from the database using the email
    conn = database.get_db_connection()
    # ----> MODIFIED THIS QUERY to include 'name' <----
    db_user = conn.execute('SELECT id, name, role, email FROM users WHERE email = ?', (email,)).fetchone() 
    conn.close()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return a complete user dictionary
    # ----> MODIFIED THIS RETURN to include 'name' <----
    # NEW CORRECTED RETURN STATEMENT
    return {"id": db_user['id'], "name": db_user['name'], "role": db_user['role'], "email": db_user['email']}

# REPLACE your old require_role function with this new one
def require_role(required_roles: List[str]):
    """
    A dependency that verifies the user is logged in and has one of
    the specified roles.
    """
    def get_user_by_role(user: dict = Depends(get_current_user)):
        user_role = user.get("role")
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of {required_roles} role(s)"
            )
        return user  # Just return the user dict we already have
    return get_user_by_role