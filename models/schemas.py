from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# Add ConfigDict to imports if not already there
from pydantic import BaseModel, ConfigDict 
# ... other imports ...

# Base model with common fields
class CourseBase(BaseModel):
    name: str
    description: str
    instructor: str

# Model for CREATING a course (doesn't need ID)
class CourseCreate(CourseBase):
    pass # Inherits all fields from CourseBase

# Model for READING/DISPLAYING a course (includes ID)
class Course(CourseBase):
    id: int

    # This allows reading data from database objects
    model_config = ConfigDict(from_attributes=True)

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

# (Inside models/schemas.py)
class Grade(BaseModel):
    id: int
    student_id: int
    course_id: int
    grade: str
    course_name: str # Add course name for display

    model_config = ConfigDict(from_attributes=True)

# (Inside models/schemas.py)
class Schedule(BaseModel):
    id: int
    course_id: int
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    course_name: str # Add course name for display

    model_config = ConfigDict(from_attributes=True)

# (Inside models/schemas.py)
class GradeCreate(BaseModel):
    student_id: int
    course_id: int
    grade: str

class ScheduleCreate(BaseModel):
    course_id: int
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None

    
    