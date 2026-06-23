import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, JSON, Table
from sqlalchemy.orm import relationship
from .database import Base

# Association Tables
teacher_grade_association = Table(
    'teacher_grade', Base.metadata,
    Column('teacher_id', String, ForeignKey('teachers.uid')),
    Column('grade_id', String, ForeignKey('grades.uid'))
)

student_subject_association = Table(
    'student_subject', Base.metadata,
    Column('student_id', String, ForeignKey('students.uid')),
    Column('subject_id', String, ForeignKey('subjects.uid'))
)

teacher_subject_association = Table(
    'teacher_subject', Base.metadata,
    Column('teacher_id', String, ForeignKey('teachers.uid')),
    Column('subject_id', String, ForeignKey('subjects.uid'))
)

grade_subject_association = Table(
    'grade_subject', Base.metadata,
    Column('grade_id', String, ForeignKey('grades.uid')),
    Column('subject_id', String, ForeignKey('subjects.uid'))
)

# USER_DB

class School(Base):
    __tablename__ = 'schools'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, unique=True, index=True)
    school_name = Column(String, nullable=False)
    email_id = Column(String)
    address = Column(String)
    district = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(Integer)
    
    teachers = relationship('Teacher', back_populates='school')
    students = relationship('Student', back_populates='school')

class Teacher(Base):
    __tablename__ = 'teachers'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = Column(String, ForeignKey('schools.uid'))
    name = Column(String, nullable=False)
    email_id = Column(String)
    phone_no = Column(String)
    
    school = relationship('School', back_populates='teachers')
    subjects = relationship('Subject', secondary=teacher_subject_association, back_populates='teachers_assigned')
    grades = relationship('Grade', secondary=teacher_grade_association, back_populates='teachers')
    chapters_completed = relationship('Chapter', back_populates='completed_by_teacher')
    lessons_created = relationship('Lesson', back_populates='created_by_teacher')

class Student(Base):
    __tablename__ = 'students'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    school_id = Column(String, ForeignKey('schools.uid'))
    roll_no = Column(String)
    phone_no = Column(String)
    grade_id = Column(String, ForeignKey('grades.uid'))
    
    school = relationship('School', back_populates='students')
    grade = relationship('Grade', back_populates='students')
    subjects = relationship('Subject', secondary=student_subject_association, back_populates='students_assigned')

# Content_Management_DB

class Grade(Base):
    __tablename__ = 'grades'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_count = Column(Integer, default=0)
    
    subjects = relationship('Subject', secondary=grade_subject_association, back_populates='grades')
    teachers = relationship('Teacher', secondary=teacher_grade_association, back_populates='grades')
    students = relationship('Student', back_populates='grade')
    chapters = relationship('Chapter', back_populates='grade')
    lessons = relationship('Lesson', back_populates='grade')

class Subject(Base):
    __tablename__ = 'subjects'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String, unique=True, index=True)
    subject_name = Column(String, nullable=False)
    chapter_count = Column(Integer, default=0)
    modules_created = Column(Integer, default=0)
    
    grades = relationship('Grade', secondary=grade_subject_association, back_populates='subjects')
    teachers_assigned = relationship('Teacher', secondary=teacher_subject_association, back_populates='subjects')
    students_assigned = relationship('Student', secondary=student_subject_association, back_populates='subjects')
    chapters = relationship('Chapter', back_populates='subject')
    lessons = relationship('Lesson', back_populates='subject')

class Chapter(Base):
    __tablename__ = 'chapters'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_name = Column(String, nullable=False)
    grade_id = Column(String, ForeignKey('grades.uid'))
    subject_id = Column(String, ForeignKey('subjects.uid'))
    completed_by = Column(String, ForeignKey('teachers.uid'))
    
    grade = relationship('Grade', back_populates='chapters')
    subject = relationship('Subject', back_populates='chapters')
    completed_by_teacher = relationship('Teacher', back_populates='chapters_completed')
    lessons = relationship('Lesson', back_populates='chapter')
    
    module_ids = Column(JSON, default=list) 

class Lesson(Base):
    __tablename__ = 'lessons'
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_name = Column(String, nullable=False)
    chapter_id = Column(String, ForeignKey('chapters.uid'))
    module_id = Column(String)
    module_content = Column(JSON)
    extra_tips = Column(JSON)
    mcq_pool = Column(String)
    homework_module_id = Column(String)
    grade_id = Column(String, ForeignKey('grades.uid'))
    subject_id = Column(String, ForeignKey('subjects.uid'))
    created_by = Column(String, ForeignKey('teachers.uid'))
    
    chapter = relationship('Chapter', back_populates='lessons')
    grade = relationship('Grade', back_populates='lessons')
    subject = relationship('Subject', back_populates='lessons')
    created_by_teacher = relationship('Teacher', back_populates='lessons_created')


from sqlalchemy import BigInteger

# Old Models (Retained)
class NoteModel(Base):
    __tablename__ = 'Notes'
    notes_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    chapter_id = Column(BigInteger,nullable=False)
    lesson_id = Column(BigInteger,nullable=False)
    content = Column(String)
    published = Column(Boolean,default=False)

class AssessmentModel(Base):
    __tablename__ = 'AssessmentPool'
    assessment_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    chapter_id = Column(BigInteger,nullable=False)
    lesson_id = Column(BigInteger,nullable=False)
    mcq_batch = Column(Integer)
    mcq_pool = Column(JSON)
    answers_pool = Column(JSON)
    published = Column(Boolean,default=False)

class HomeworkModel(Base):
    __tablename__ = 'Homework'
    homework_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    chapter_id = Column(BigInteger,nullable=False)
    lesson_id = Column(BigInteger,nullable=False)
    homework_questions = Column(JSON)
    published = Column(Boolean,default=False)