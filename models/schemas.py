from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

# --- User Models ---
class User(BaseModel):
    name: str
    email: str
    password: str
    role: str

class UserDisplay(BaseModel):
    model_config = ConfigDict(from_attributes=True) 
    id: int
    name: str
    email: str
    role: str

# --- Chat Models ---
class ChatQuery(BaseModel):
    message: str

class Chat(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    message: str
    response: str
    timestamp: datetime # Will be read from DB

# --- Course Models ---
class CourseBase(BaseModel):
    name: str
    description: str
    instructor: str

class CourseCreate(CourseBase):
    pass # For creating a new course

class Course(CourseBase):
    id: int
    model_config = ConfigDict(from_attributes=True) 

# --- Grade Models ---
class GradeCreate(BaseModel):
    student_id: int
    course_id: int
    grade: str

class Grade(BaseModel):
    id: int
    student_id: int
    course_id: int
    grade: str
    course_name: str # From the JOIN query
    model_config = ConfigDict(from_attributes=True)

# --- Schedule Models ---
class ScheduleCreate(BaseModel):
    course_id: int
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None

class Schedule(BaseModel):
    id: int
    course_id: int
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    course_name: str # From the JOIN query
    model_config = ConfigDict(from_attributes=True)

# --- Enrollment Models (THE MISSING CLASS) ---
class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int




    
    