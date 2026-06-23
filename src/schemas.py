from pydantic import BaseModel, computed_field
from typing import List, Dict, Optional, Any

class GoalRequest(BaseModel):
    goal: str
    chapter_id: Optional[int] = None
    lesson_id: Optional[int] = None


# --- Old schemas (retained) ---
class NoteCreate(BaseModel):
    title: str
    chapter_id : int
    lesson_id : int
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    chapter_id: Optional[int] = None
    lesson_id: Optional[int] = None
    content: Optional[str] = None
    published: Optional[bool] = None

class Note(BaseModel):
    notes_id: int
    title: str
    chapter_id : int
    lesson_id : int
    content: str
    published: bool
    
    class Config:
        orm_mode = True
        from_attributes = True

class AssessmentCreate(BaseModel):
    title: str
    chapter_id: int
    lesson_id: int
    mcq_batch: int
    mcq_pool: List[Dict]
    answers_pool: List[Dict]

class AssessmentUpdate(BaseModel):
    title: Optional[str] = None
    chapter_id: Optional[int] = None
    lesson_id: Optional[int] = None
    mcq_batch: Optional[int] = None
    mcq_pool: Optional[Any] = None
    answers_pool: Optional[Any] = None
    published: Optional[bool] = None

class Assessment(BaseModel):
    assessment_id : int
    title: str
    chapter_id : int
    lesson_id : int
    mcq_batch : int
    mcq_pool : str
    answers_pool : str
    published : bool
    
    class Config:
        orm_mode = True
        from_attributes = True

class HomeworkCreate(BaseModel):
    title: str
    chapter_id: int
    lesson_id: int
    homework_questions: List[Dict]

class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    chapter_id: Optional[int] = None
    lesson_id: Optional[int] = None
    homework_questions: Optional[Any] = None
    published: Optional[bool] = None

class Homework(BaseModel):
    homework_id : int
    title: str
    chapter_id : int
    lesson_id : int
    homework_questions: str
    published : bool

    class Config:
        orm_mode = True
        from_attributes = True

# --- New Schemas ---

class SchoolBase(BaseModel):
    school_id: str
    school_name: str
    email_id: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[int] = None

class SchoolCreate(SchoolBase):
    pass

class SchoolOut(SchoolBase):
    uid: str
    class Config:
        orm_mode = True
        from_attributes = True

class StudentBase(BaseModel):
    student_id: str
    name: str
    school_id: Optional[str] = None
    roll_no: Optional[str] = None
    phone_no: Optional[str] = None
    grade_id: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentOut(StudentBase):
    uid: str
    class Config:
        orm_mode = True
        from_attributes = True

class TeacherBase(BaseModel):
    name: str
    school_id: Optional[str] = None
    email_id: Optional[str] = None
    phone_no: Optional[str] = None

class TeacherCreate(TeacherBase):
    pass

class TeacherOut(TeacherBase):
    uid: str
    class Config:
        orm_mode = True
        from_attributes = True

class GradeBase(BaseModel):
    student_count: Optional[int] = 0

class GradeCreate(GradeBase):
    pass

class GradeOut(GradeBase):
    uid: str

    @computed_field
    def id(self) -> str:
        return self.uid

    @computed_field
    def grade(self) -> str:
        if isinstance(self.uid, str) and self.uid.startswith("GRD"):
            try:
                # GRD001 maps to Grade 9, GRD002 to Grade 10, etc.
                return str(int(self.uid[3:]) + 8)
            except ValueError:
                pass
        return str(self.uid)

    class Config:
        orm_mode = True
        from_attributes = True

class SubjectBase(BaseModel):
    subject_id: str
    subject_name: str
    chapter_count: Optional[int] = 0
    modules_created: Optional[int] = 0

class SubjectCreate(SubjectBase):
    pass

class SubjectOut(SubjectBase):
    uid: str

    @computed_field
    def id(self) -> str:
        return self.uid

    class Config:
        orm_mode = True
        from_attributes = True

class ChapterBase(BaseModel):
    chapter_name: str
    grade_id: Optional[str] = None
    subject_id: Optional[str] = None
    completed_by: Optional[str] = None
    module_ids: Optional[List[str]] = []

class ChapterCreate(ChapterBase):
    pass

class ChapterOut(ChapterBase):
    uid: str

    @computed_field
    def id(self) -> str:
        return self.uid

    @computed_field
    def slug(self) -> str:
        return self.chapter_name.lower().replace(" ", "-") if self.chapter_name else self.uid

    class Config:
        orm_mode = True
        from_attributes = True

class LessonBase(BaseModel):
    lesson_name: str
    chapter_id: Optional[str] = None
    module_id: Optional[str] = None
    module_content: Optional[Any] = None
    extra_tips: Optional[Any] = None
    mcq_pool: Optional[str] = None
    homework_module_id: Optional[str] = None
    grade_id: Optional[str] = None
    subject_id: Optional[str] = None
    created_by: Optional[str] = None

class LessonCreate(LessonBase):
    pass

class LessonOut(LessonBase):
    uid: str

    @computed_field
    def id(self) -> str:
        return self.uid

    @computed_field
    def slug(self) -> str:
        return self.lesson_name.lower().replace(" ", "-") if getattr(self, 'lesson_name', None) else self.uid

    class Config:
        orm_mode = True
        from_attributes = True