from pydantic import BaseModel, ConfigDict, conint, computed_field
from datetime import datetime
from typing import Optional 

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
    year_of_study: int

class CourseCreate(CourseBase):
    pass # For creating a new course

class CourseCreate(CourseBase):
    pass # Will inherit year_of_study

class Course(CourseBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Course(CourseBase):
    id: int
    model_config = ConfigDict(from_attributes=True) 

class InternalMarkBase(BaseModel):
    # Pydantic validation: allows integers between 0 and 25
    internal_1: conint(ge=0, le=25) = 0
    internal_2: conint(ge=0, le=25) = 0
    internal_3: conint(ge=0, le=25) = 0

class InternalMarkCreate(InternalMarkBase):
    student_id: int
    course_id: int

class InternalMarkDisplay(InternalMarkBase):
    model_config = ConfigDict(from_attributes=True) # For reading from DB
    
    course_name: str
    student_name: str
    
    # This automatically calculates the total from the other 3 fields
    @computed_field
    @property
    def total_marks(self) -> int:
        return self.internal_1 + self.internal_2 + self.internal_3

    # This automatically calculates the status based on your 35% rule
    @computed_field
    @property
    def status(self) -> str:
        # 35% of 75 = 26.25
        pass_mark = 26.25 
        if self.total_marks >= pass_mark:
            return "Average marks"
        else:
            return "No avarage Marks"

# --- Schedule Models ---
class ScheduleCreate(BaseModel):
    course_id: int
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None

class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    course_name: str # From the JOIN query

# --- Enrollment Models ---
class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int

# --- Admin Models (THE MISSING CLASS) ---
class PromptUpdate(BaseModel):
    prompt: str

class User(BaseModel):
    name: str
    email: str
    password: str
    role: str
    year_of_study: Optional[int] = None # <-- ADD THIS

class UserDisplay(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    year_of_study: Optional[int] = None # <-- ADD THIS





    
    