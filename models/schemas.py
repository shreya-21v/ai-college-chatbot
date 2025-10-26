from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# Pydantic model for a Course
class Course(BaseModel):
    name: str
    description: str
    instructor: str

# ... (other models like User, Course, etc.)

class ChatQuery(BaseModel):
    message: str

# Pydantic model for a Chat message
class Chat(BaseModel):
    user_id: int
    message: str
    response: str
    timestamp: Optional[datetime] = None # Optional, can be set by server

# Pydantic model for a User
class User(BaseModel):
    name: str
    email: str
    password: str
    role: str

# This is a model for *displaying* a user, which hides the password
class UserDisplay(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str

    
    