import re

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .models import NoteModel, AssessmentModel
from .database import Base, engine, SessionLocal, get_db
from . import schemas, models
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import requests            #3rd alternative
from typing import List, Optional
import json

app = FastAPI(
    title= "content Generation",
    description="API is for AI to generate content",
)

# Add CORS middleware, 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "https://triallms-react.vercel.app"],  # Add your frontend origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

load_dotenv()

Base.metadata.create_all(bind=engine)

print("!<----Connecting with Hugging Face---->!")

####3rd Alternative Using Manual Headers & constructing payload

API_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {os.getenv('HUGGINGFACEHUB_API_TOKEN')}",
    "Content-Type": "application/json"
}


#llm = ChatOpenAI(
#    base_url="https://router.huggingface.co/v1",
#    api_key=os.getenv('HUGGINGFACEHUB_API_TOKEN'),
#    model='mistralai/Mistral-7B-Instruct-v0.2:featherless-ai',
#    temperature=0.7,
#    max_tokens = 500
#)

print("!<----Sanity check for GET request API---->!")
@app.get('/')
def sanity():
    return {"message":"API is working"}


def extract_numeric_id(uid: str) -> int:
    if not uid:
        return 1
    digits = "".join(filter(str.isdigit, str(uid)))
    return int(digits[:12]) if digits else 1

##API & path to create notes
@app.post('/create-note')
def create_note(note:schemas.NoteCreate, db:Session = Depends(get_db)):
    db_note = models.NoteModel(
        title = note.title,
        chapter_id = note.chapter_id,
        lesson_id = note.lesson_id,
        content=note.content
        )
    # inserting notes into DB
    print("!<----Inserting note to table---->!")
    db.add(db_note)
    print("!<----Finalizing Commit---->!")
    db.commit()
    print("!<----Refreshing Database....---->!")
    db.refresh(db_note)
    return db_note


@app.get('/note')
def get_note(
    notes_id: Optional[int] = Query(None),
    title: Optional[str] = Query(None),
    chapter_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):

    query = db.query(models.NoteModel)

    # Filter by notes_id
    if notes_id is not None:
        query = query.filter(models.NoteModel.notes_id == notes_id)

    # Filter by title (case-insensitive partial match)
    if title is not None:
        query = query.filter(models.NoteModel.title.ilike(f"%{title}%"))

    # Filter by chapter_id
    if chapter_id is not None:
        query = query.filter(models.NoteModel.chapter_id == chapter_id)

    results = query.all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No notes found"
        )

    chapters = db.query(models.Chapter).all()
    lessons = db.query(models.Lesson).all()
    
    chapter_map = {extract_numeric_id(c.uid): c.chapter_name for c in chapters}
    lesson_map = {extract_numeric_id(l.uid): l.lesson_name for l in lessons}
    
    output = []
    for r in results:
        output.append({
            "notes_id": r.notes_id,
            "title": r.title,
            "chapter_id": r.chapter_id,
            "lesson_id": r.lesson_id,
            "content": r.content,
            "published": getattr(r, "published", False),
            "chapter_name": chapter_map.get(r.chapter_id, "Unknown Chapter"),
            "lesson_name": lesson_map.get(r.lesson_id, "Unknown Lesson")
        })

    return output


### API & path to update notes 
@app.put('/update-note/{notes_id}')
def update_note(
    notes_id: int,
    note: schemas.NoteUpdate,
    db: Session = Depends(get_db)
):

    # Find existing note
    db_note = db.query(models.NoteModel).filter(
        models.NoteModel.notes_id == notes_id
    ).first()

    # Check if note exists
    if not db_note:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    # Update only provided fields
    if note.title is not None:
        db_note.title = note.title

    if note.chapter_id is not None:
        db_note.chapter_id = note.chapter_id

    if note.lesson_id is not None:
        db_note.lesson_id = note.lesson_id

    if note.content is not None:
        db_note.content = note.content

    if note.published is not None:
        db_note.published = note.published

    print("!<----Updating Note---->!")

    # Commit changes
    db.commit()

    print("!<----Refreshing Updated Note---->!")

    # Refresh updated object
    db.refresh(db_note)

    return db_note


##API & Path to delete tasks
@app.delete('/delete-note/{notes_id}')
def delete_note(notes_id:int, db:Session = Depends(get_db)):
    print("!<----querying DB in search of Index---->!")
    db_note = db.query(models.NoteModel).filter(models.NoteModel.notes_id==notes_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail='Note not present in DB')
    db.delete(db_note)
    print("!<----Removing row from database---->!")
    db.commit()
    print("!<----Finalizing Commit---->!")

    return {"message": "Note has been Deleted", 'note': db_note}

##API for fetch all Notes
@app.get('/notes')
def get_all_notes(db:Session = Depends(get_db)):
    notes = db.query(models.NoteModel).all()
    
    chapters = db.query(models.Chapter).all()
    lessons = db.query(models.Lesson).all()
    
    chapter_map = {extract_numeric_id(c.uid): c.chapter_name for c in chapters}
    lesson_map = {extract_numeric_id(l.uid): l.lesson_name for l in lessons}
    
    output = []
    for r in notes:
        output.append({
            "notes_id": r.notes_id,
            "title": r.title,
            "chapter_id": r.chapter_id,
            "lesson_id": r.lesson_id,
            "content": r.content,
            "published": getattr(r, "published", False),
            "chapter_name": chapter_map.get(r.chapter_id, "Unknown Chapter"),
            "lesson_name": lesson_map.get(r.lesson_id, "Unknown Lesson")
        })

    return output


##API to communicate with AI model
#def generate_notes(goal:str):
#    prompt = """
#goal : {goal}
#Create Short Summarization of the topics & headings
#content should be student friendly & well defined for educational purpose
#"""
#    
#    response = llm.invoke(prompt)
#    print("!<----Prompt has been initiated---->!")
#    notes = {}
#    return notes

# AI API to create notes
def generate_notes(goal: str):

    prompt = f"""
    Goal: {goal}

    Create short educational notes.
    """

    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload
    )

    data = response.json()

    print(data)

    content = data["choices"][0]["message"]["content"]

    notes = [
        {
            "title": "Generated Notes",
            "chapter_id": 1,
            "lesson_id": 1,
            "content": content
        }
    ]

    return notes

    
###
#@app.post('/notes/generate')
#def generate_note(goals:schemas.GoalRequest,db:Session = Depends(get_db)):
#    notes = generate_notes(goals.goal)
#    created_notes = []
#    for note in notes:
#        created_notes = notes
#        db_note = models.NoteModel(title= notes.title)
#        db.add(db_note)
#        db.commit()
#        db.refresh(db_note)

    


@app.post('/notes/generate')
def generate_note(
    goals: schemas.GoalRequest,
    db: Session = Depends(get_db)
):

    notes = generate_notes(goals.goal)

    created_notes = []

    for note in notes:

        c_id = goals.chapter_id if goals.chapter_id else note["chapter_id"]
        l_id = goals.lesson_id if goals.lesson_id else note["lesson_id"]

        db_note = models.NoteModel(
            title=note["title"],
            chapter_id=c_id,
            lesson_id=l_id,
            content=note["content"]
        )

        db.add(db_note)
        created_notes.append(db_note)

    db.commit()

    for note in created_notes:
        db.refresh(note)

    return created_notes


print("<!---- Assessment API for creating MCQ's ----!>")


### API & path to create assessment
@app.post('/create-assessment')
def create_assessment(
    assessment: schemas.AssessmentCreate,
    db: Session = Depends(get_db)
):
    db_assessment = models.AssessmentModel(
        title=assessment.title,
        chapter_id=assessment.chapter_id,
        lesson_id=assessment.lesson_id,
        mcq_batch=assessment.mcq_batch,
        mcq_pool=assessment.mcq_pool,
        answers_pool=assessment.answers_pool
    )

    # inserting assessment into DB
    print("!<----Inserting assessment to table---->!")
    db.add(db_assessment)

    print("!<----Finalizing Commit---->!")
    db.commit()

    print("!<----Refreshing Database....---->!")
    db.refresh(db_assessment)

    return db_assessment


### API to fetch single Assessment 
@app.get('/assessment')
def get_assessment(
    assessment_id: Optional[int] = Query(None),
    title: Optional[str] = Query(None),
    chapter_id: Optional[int] = Query(None),
    lesson_id: Optional[int] = Query(None),
    published: Optional[bool] = Query(None),
    mcq_batch: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):

    query = db.query(models.AssessmentModel)

    # Filter by assessment_id
    if assessment_id is not None:
        query = query.filter(models.AssessmentModel.assessment_id == assessment_id)

    # Filter by title (partial match, case-insensitive)
    if title is not None:
        query = query.filter(models.AssessmentModel.title.ilike(f"%{title}%"))

    # Filter by chapter_id
    if chapter_id is not None:
        query = query.filter(models.AssessmentModel.chapter_id == chapter_id)

    # Filter by lesson_id
    if lesson_id is not None:
        query = query.filter(models.AssessmentModel.lesson_id == lesson_id)

    # Filter by published status
    if published is not None:
        query = query.filter(models.AssessmentModel.published == published)

    # Filter by mcq_batch
    if mcq_batch is not None:
        query = query.filter(models.AssessmentModel.mcq_batch == mcq_batch)

    results = query.all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No assessments found"
        )

    chapters = db.query(models.Chapter).all()
    lessons = db.query(models.Lesson).all()
    
    chapter_map = {extract_numeric_id(c.uid): c.chapter_name for c in chapters}
    lesson_map = {extract_numeric_id(l.uid): l.lesson_name for l in lessons}
    
    output = []
    for r in results:
        output.append({
            "assessment_id": r.assessment_id,
            "title": r.title,
            "chapter_id": r.chapter_id,
            "lesson_id": r.lesson_id,
            "mcq_batch": r.mcq_batch,
            "mcq_pool": r.mcq_pool,
            "answers_pool": r.answers_pool,
            "published": r.published,
            "chapter_name": chapter_map.get(r.chapter_id, "Unknown Chapter"),
            "lesson_name": lesson_map.get(r.lesson_id, "Unknown Lesson")
        })

    return output

###API to Update Single Assessment
@app.put('/update-assessment/{assessment_id}')
def update_assessment(
    assessment_id: int,
    assessment: schemas.AssessmentUpdate,
    db: Session = Depends(get_db)
):

    # Find existing assessment
    db_assessment = db.query(models.AssessmentModel).filter(
        models.AssessmentModel.assessment_id == assessment_id
    ).first()

    # Check if exists
    if not db_assessment:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found"
        )

    # Update only provided fields
    if assessment.title is not None:
        db_assessment.title = assessment.title

    if assessment.chapter_id is not None:
        db_assessment.chapter_id = assessment.chapter_id

    if assessment.lesson_id is not None:
        db_assessment.lesson_id = assessment.lesson_id

    if assessment.mcq_batch is not None:
        db_assessment.mcq_batch = assessment.mcq_batch

    if assessment.mcq_pool is not None:
        db_assessment.mcq_pool = assessment.mcq_pool

    if assessment.answers_pool is not None:
        db_assessment.answers_pool = assessment.answers_pool

    if assessment.published is not None:
        db_assessment.published = assessment.published

    print("!<----Updating Assessment---->!")

    # Commit changes
    db.commit()

    print("!<----Refreshing Updated Assessment---->!")

    # Refresh object
    db.refresh(db_assessment)

    return db_assessment

##API & Path to delete Assessments
@app.delete('/delete-assessment/{assessment_id}')
def delete_assessment(assessment_id:int, db:Session = Depends(get_db)):
    print("!<----querying DB in search of Index---->!")
    db_assessment = db.query(models.AssessmentModel).filter(models.AssessmentModel.assessment_id==assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=404, detail='Assessment not present in DB')
    db.delete(db_assessment)
    print("!<----Removing row from database---->!")
    db.commit()
    print("!<----Finalizing Commit---->!")

    return {"message": "Assessment has been Deleted", 'assessment': db_assessment}



### API for fetch all Assessment
@app.get('/assessments')
def get_all_assessments(db:Session = Depends(get_db)):
    assessments = db.query(models.AssessmentModel).all()
    
    chapters = db.query(models.Chapter).all()
    lessons = db.query(models.Lesson).all()
    
    chapter_map = {extract_numeric_id(c.uid): c.chapter_name for c in chapters}
    lesson_map = {extract_numeric_id(l.uid): l.lesson_name for l in lessons}
    
    output = []
    for r in assessments:
        output.append({
            "assessment_id": r.assessment_id,
            "title": r.title,
            "chapter_id": r.chapter_id,
            "lesson_id": r.lesson_id,
            "mcq_batch": r.mcq_batch,
            "mcq_pool": r.mcq_pool,
            "answers_pool": r.answers_pool,
            "published": r.published,
            "chapter_name": chapter_map.get(r.chapter_id, "Unknown Chapter"),
            "lesson_name": lesson_map.get(r.lesson_id, "Unknown Lesson")
        })
        
    return output



### API to send request to AI to generate assessment
def generate_assessment(goal: str):

    prompt = f"""
    Goal: {goal}

    Generate an educational assessment in JSON format.

    Requirements:
    - Create 5 MCQs
    - Each MCQ should have:
      - question
      - 4 options
      - correct answer

    Return ONLY valid JSON in this format:

    {{
      "title": "Assessment Title",
      "chapter_id": 1,
      "lesson_id": 1,
      "mcq_batch": 5,
      "mcq_pool": [
        {{
          "question": "...",
          "options": ["A", "B", "C", "D"]
        }}
      ],
      "answers_pool": [
        {{
          "question": "...",
          "answer": "..."
        }}
      ]
    }}
    """

    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1500,
        "temperature": 0.7
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload
    )

    data = response.json()

    print(data)

    content = data["choices"][0]["message"]["content"]

    # Convert AI response string into Python dict
    assessment_data = json.loads(content)

    # Create schema object
    assessment = schemas.AssessmentCreate(
        title=assessment_data["title"],
        chapter_id=assessment_data["chapter_id"],
        lesson_id=assessment_data["lesson_id"],
        mcq_batch=assessment_data["mcq_batch"],
        mcq_pool=assessment_data["mcq_pool"],
        answers_pool=assessment_data["answers_pool"]
    )

    return assessment



# API to generate assessment and save to database

@app.post('/assessment/generate')
def generate_assessment_api(
    goals: schemas.GoalRequest,
    db: Session = Depends(get_db)
):

    # Generate assessment using AI
    assessment = generate_assessment(goals.goal)

    # Use explicit IDs if provided, else what AI hallucinated
    c_id = goals.chapter_id if goals.chapter_id else assessment.chapter_id
    l_id = goals.lesson_id if goals.lesson_id else assessment.lesson_id

    # Create DB object
    db_assessment = models.AssessmentModel(
        title=assessment.title,
        chapter_id=c_id,
        lesson_id=l_id,
        mcq_batch=assessment.mcq_batch,
        mcq_pool=assessment.mcq_pool,
        answers_pool=assessment.answers_pool
    )

    print("!<----Inserting assessment into DB---->!")

    db.add(db_assessment)

    print("!<----Committing Changes---->!")

    db.commit()

    print("!<----Refreshing DB Object---->!")

    db.refresh(db_assessment)

    return db_assessment




print("<!---- HomeWork API for creating HomeWork Questions ----!>")

### API & path to create HomeWork
@app.post('/create-homework')
def create_homework(
    homework: schemas.HomeworkCreate,
    db: Session = Depends(get_db)
):
    db_homework = models.HomeworkModel(
        title=homework.title,
        chapter_id=homework.chapter_id,
        lesson_id=homework.lesson_id,
        homework_questions=homework.homework_questions
    )

    # inserting assessment into DB
    print("!<----Inserting HomeWork questions to table---->!")
    db.add(db_homework)

    print("!<----Finalizing Commit---->!")
    db.commit()

    print("!<----Refreshing Database....---->!")
    db.refresh(db_homework)

    return db_homework

### API to update homework based on {homework_id}
@app.put('/update-homework/{homework_id}')
def update_homework(
    homework_id: int,
    homework: schemas.HomeworkUpdate,
    db: Session = Depends(get_db)
):

    # Find existing homework
    db_homework = db.query(models.HomeworkModel).filter(
        models.HomeworkModel.homework_id == homework_id
    ).first()

    # Check if exists
    if not db_homework:
        raise HTTPException(
            status_code=404,
            detail="Homework not found"
        )

    # Update only provided fields
    if homework.title is not None:
        db_homework.title = homework.title

    if homework.chapter_id is not None:
        db_homework.chapter_id = homework.chapter_id

    if homework.lesson_id is not None:
        db_homework.lesson_id = homework.lesson_id

    if homework.homework_questions is not None:
        db_homework.homework_questions = homework.homework_questions

    if homework.published is not None:
        db_homework.published = homework.published

    print("!<----Updating Homework---->!")

    # Commit changes
    db.commit()

    print("!<----Refreshing Updated Homework---->!")

    # Refresh updated object
    db.refresh(db_homework)

    return db_homework


##API & Path to delete Homework
@app.delete('/delete-homework/{homework_id}')
def delete_homework(homework_id:int, db:Session = Depends(get_db)):
    print("!<----querying DB in search of Index---->!")
    db_homework = db.query(models.HomeworkModel).filter(models.HomeworkModel.homework_id==homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail='Homework not present in DB')
    db.delete(db_homework)
    print("!<----Removing row from database---->!")
    db.commit()
    print("!<----Finalizing Commit---->!")

    return {"message": "Homework has been Deleted", 'homework': db_homework}


### API for fetch all Homework
@app.get('/homeworks')
def get_all_homeworks(db:Session = Depends(get_db)):
    homeworks = db.query(models.HomeworkModel).all()
    
    chapters = db.query(models.Chapter).all()
    lessons = db.query(models.Lesson).all()
    
    chapter_map = {extract_numeric_id(c.uid): c.chapter_name for c in chapters}
    lesson_map = {extract_numeric_id(l.uid): l.lesson_name for l in lessons}
    
    output = []
    for r in homeworks:
        output.append({
            "homework_id": r.homework_id,
            "title": r.title,
            "chapter_id": r.chapter_id,
            "lesson_id": r.lesson_id,
            "homework_questions": r.homework_questions,
            "published": getattr(r, "published", False),
            "chapter_name": chapter_map.get(r.chapter_id, "Unknown Chapter"),
            "lesson_name": lesson_map.get(r.lesson_id, "Unknown Lesson")
        })

    return output


### API to fetch single homework
@app.get('/homework')
def get_homework(
    homework_id: Optional[int] = Query(None),
    title: Optional[str] = Query(None),
    chapter_id: Optional[int] = Query(None),
    lesson_id: Optional[int] = Query(None),
    published: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):

    query = db.query(models.HomeworkModel)

    # Filter by homework_id
    if homework_id is not None:
        query = query.filter(models.HomeworkModel.homework_id == homework_id)

    # Filter by title (case-insensitive partial match)
    if title is not None:
        query = query.filter(models.HomeworkModel.title.ilike(f"%{title}%"))

    # Filter by chapter_id
    if chapter_id is not None:
        query = query.filter(models.HomeworkModel.chapter_id == chapter_id)

    # Filter by lesson_id
    if lesson_id is not None:
        query = query.filter(models.HomeworkModel.lesson_id == lesson_id)

    # Filter by published status
    if published is not None:
        query = query.filter(models.HomeworkModel.published == published)

    results = query.all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No homework found"
        )

    chapters = db.query(models.Chapter).all()
    lessons = db.query(models.Lesson).all()
    
    chapter_map = {extract_numeric_id(c.uid): c.chapter_name for c in chapters}
    lesson_map = {extract_numeric_id(l.uid): l.lesson_name for l in lessons}
    
    output = []
    for r in results:
        output.append({
            "homework_id": r.homework_id,
            "title": r.title,
            "chapter_id": r.chapter_id,
            "lesson_id": r.lesson_id,
            "homework_module": r.homework_module,
            "published": getattr(r, "published", False),
            "chapter_name": chapter_map.get(r.chapter_id, "Unknown Chapter"),
            "lesson_name": lesson_map.get(r.lesson_id, "Unknown Lesson")
        })

    return output

### API to send request to AI to generate homework

def generate_homework(goal: str):

    prompt = f"""
Goal: {goal}

You are a strict JSON generator.

CRITICAL RULES:
- Return ONLY a single JSON object (NOT an array)
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include notes
- Do NOT include any text outside JSON
- Do NOT wrap output in ``` or ```json
- Do NOT return a list/array at top level

You will be penalized for invalid JSON.

Generate exactly 5 homework questions and their short answers.

Each question must contain:
- question (string)
- answer (string)

Return ONLY valid JSON in this format:

{{
  "title": "Homework Title",
  "chapter_id": 1,
  "lesson_id": 1,
  "homework_questions": [
    {{
      "question": "...",
      "answer": "..."
    }}
  ]
}}
"""

    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.3
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload
    )

    data = response.json()

    print("FULL API RESPONSE:", data)

    content = data["choices"][0]["message"]["content"]

    print("RAW AI RESPONSE:", content)

    # Clean markdown if any
    content = content.replace("```json", "").replace("```", "").strip()

    # Remove control characters
    content = re.sub(r'[\x00-\x1F\x7F]', '', content)

    try:
        decoder = json.JSONDecoder()
        homework_data, _ = decoder.raw_decode(content)

    except json.JSONDecodeError as e:

        print("JSON ERROR:", e)

        # aggressive fix
        fixed_content = content.replace("\\", "\\\\")
        fixed_content = re.sub(r'[\x00-\x1F\x7F]', '', fixed_content)

        decoder = json.JSONDecoder()
        homework_data, _ = decoder.raw_decode(fixed_content)

    # 🔥 FIX: handle list output from model
    if isinstance(homework_data, list):
        homework_data = homework_data[0]

    # final schema mapping
    homework = schemas.HomeworkCreate(
        title=homework_data["title"],
        chapter_id=homework_data["chapter_id"],
        lesson_id=homework_data["lesson_id"],
        homework_questions=homework_data["homework_questions"]
    )

    return homework


# API to generate homework and save to database

@app.post('/homework/generate')
def generate_homework_api(
    goals: schemas.GoalRequest,
    db: Session = Depends(get_db)
):

    # Generate homework using AI
    homework = generate_homework(goals.goal)

    c_id = goals.chapter_id if goals.chapter_id else homework.chapter_id
    l_id = goals.lesson_id if goals.lesson_id else homework.lesson_id

    # Create DB object
    db_homework = models.HomeworkModel(
        title=homework.title,
        chapter_id=c_id,
        lesson_id=l_id,
        homework_questions=homework.homework_questions
    )

    print("!<----Inserting homework into DB---->!")

    db.add(db_homework)

    print("!<----Committing Changes---->!")

    db.commit()

    print("!<----Refreshing DB Object---->!")

    db.refresh(db_homework)

    return db_homework


print("<!---- Extra Tips API for creating Extra Tips based on Notes generated----!>")
# --- NEW API ENDPOINTS FOR USER_DB AND Content_Management_DB ---

# Schools
@app.get('/schools/', response_model=List[schemas.SchoolOut])
def get_schools(db: Session = Depends(get_db)):
    return db.query(models.School).all()

@app.post('/schools/', response_model=schemas.SchoolOut)
def create_school(school: schemas.SchoolCreate, db: Session = Depends(get_db)):
    db_school = models.School(**school.dict())
    db.add(db_school)
    db.commit()
    db.refresh(db_school)
    return db_school

# Teachers
@app.get('/teachers/', response_model=List[schemas.TeacherOut])
def get_teachers(db: Session = Depends(get_db)):
    return db.query(models.Teacher).all()

@app.post('/teachers/', response_model=schemas.TeacherOut)
def create_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    db_teacher = models.Teacher(**teacher.dict())
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher

@app.get('/teachers/{teacher_id}/grades', response_model=List[schemas.GradeOut])
def get_teacher_grades(teacher_id: str, db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.uid == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher.grades

@app.get('/teachers/{teacher_id}/grades/{grade_id}/subjects', response_model=List[schemas.SubjectOut])
def get_teacher_subjects(teacher_id: str, grade_id: str, db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.uid == teacher_id).first()
    grade = db.query(models.Grade).filter(models.Grade.uid == grade_id).first()
    if not teacher or not grade:
        raise HTTPException(status_code=404, detail="Not found")
    
    teacher_subjects = {s.uid: s for s in teacher.subjects}
    grade_subjects = {s.uid: s for s in grade.subjects}
    
    intersected_subjects = [s for uid, s in teacher_subjects.items() if uid in grade_subjects]
    return intersected_subjects

@app.get('/teachers/{teacher_id}/content')
def get_teacher_content(teacher_id: str, grade_id: str, subject_id: str, db: Session = Depends(get_db)):
    chapters = db.query(models.Chapter).filter(
        models.Chapter.completed_by == teacher_id,
        models.Chapter.grade_id == grade_id,
        models.Chapter.subject_id == subject_id
    ).all()
    
    grouped_chapters = {}
    for chapter in chapters:
        c_name = chapter.chapter_name
        if c_name not in grouped_chapters:
            grouped_chapters[c_name] = {
                "chapter_id": extract_numeric_id(chapter.uid),
                "chapter_name": c_name,
                "lessons": {}
            }
            
        for lesson in chapter.lessons:
            l_name = lesson.lesson_name
            if l_name not in grouped_chapters[c_name]["lessons"]:
                grouped_chapters[c_name]["lessons"][l_name] = {
                    "lesson_id": extract_numeric_id(lesson.uid),
                    "lesson_name": l_name,
                    "assessments": [],
                    "homeworks": [],
                    "notes": []
                }
            
            assessments = db.query(models.AssessmentModel).filter(models.AssessmentModel.lesson_id == extract_numeric_id(lesson.uid)).all()
            for a in assessments:
                if not any(existing["id"] == a.assessment_id for existing in grouped_chapters[c_name]["lessons"][l_name]["assessments"]):
                    grouped_chapters[c_name]["lessons"][l_name]["assessments"].append({"id": a.assessment_id, "title": a.title})
                    
            homeworks = db.query(models.HomeworkModel).filter(models.HomeworkModel.lesson_id == extract_numeric_id(lesson.uid)).all()
            for h in homeworks:
                if not any(existing["id"] == h.homework_id for existing in grouped_chapters[c_name]["lessons"][l_name]["homeworks"]):
                    grouped_chapters[c_name]["lessons"][l_name]["homeworks"].append({"id": h.homework_id, "title": h.title})

            notes = db.query(models.NoteModel).filter(models.NoteModel.lesson_id == extract_numeric_id(lesson.uid)).all()
            for n in notes:
                if not any(existing["id"] == n.notes_id for existing in grouped_chapters[c_name]["lessons"][l_name]["notes"]):
                    grouped_chapters[c_name]["lessons"][l_name]["notes"].append({"id": n.notes_id, "title": n.title})

    result = []
    for c_name, c_data in grouped_chapters.items():
        c_data["lessons"] = list(c_data["lessons"].values())
        result.append(c_data)
        
    return result

# Students
@app.get('/students/', response_model=List[schemas.StudentOut])
def get_students(db: Session = Depends(get_db)):
    return db.query(models.Student).all()

@app.post('/students/', response_model=schemas.StudentOut)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = models.Student(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get('/students/{student_id}/info')
def get_student_info(student_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.uid == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    grade = student.grade
    if not grade:
        return {"grade": None, "subjects": []}
        
    subjects = student.subjects
    
    grade_val = grade.uid
    if str(grade_val).startswith("GRD"):
        try:
            grade_val = str(int(grade_val[3:]) + 8)
        except ValueError:
            pass

    return {
        "grade": {
            "uid": grade.uid,
            "grade": grade_val
        },
        "subjects": [{"uid": s.uid, "subject_name": s.subject_name} for s in subjects]
    }

@app.get('/students/{student_id}/content')
def get_student_content(student_id: str, subject_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.uid == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    chapters = db.query(models.Chapter).filter(
        models.Chapter.grade_id == student.grade_id,
        models.Chapter.subject_id == subject_id
    ).all()
    
    grouped_chapters = {}
    for chapter in chapters:
        c_name = chapter.chapter_name
        if c_name not in grouped_chapters:
            grouped_chapters[c_name] = {
                "chapter_id": extract_numeric_id(chapter.uid),
                "chapter_name": c_name,
                "lessons": {}
            }
            
        for lesson in chapter.lessons:
            l_name = lesson.lesson_name
            if l_name not in grouped_chapters[c_name]["lessons"]:
                grouped_chapters[c_name]["lessons"][l_name] = {
                    "lesson_id": extract_numeric_id(lesson.uid),
                    "lesson_name": l_name,
                    "assessments": [],
                    "homeworks": [],
                    "notes": []
                }
            
            assessments = db.query(models.AssessmentModel).filter(models.AssessmentModel.lesson_id == extract_numeric_id(lesson.uid)).all()
            for a in assessments:
                if not any(existing["id"] == a.assessment_id for existing in grouped_chapters[c_name]["lessons"][l_name]["assessments"]):
                    grouped_chapters[c_name]["lessons"][l_name]["assessments"].append({"id": a.assessment_id, "title": a.title})
                    
            homeworks = db.query(models.HomeworkModel).filter(models.HomeworkModel.lesson_id == extract_numeric_id(lesson.uid)).all()
            for h in homeworks:
                if not any(existing["id"] == h.homework_id for existing in grouped_chapters[c_name]["lessons"][l_name]["homeworks"]):
                    grouped_chapters[c_name]["lessons"][l_name]["homeworks"].append({"id": h.homework_id, "title": h.title})

            notes = db.query(models.NoteModel).filter(models.NoteModel.lesson_id == extract_numeric_id(lesson.uid)).all()
            for n in notes:
                if not any(existing["id"] == n.notes_id for existing in grouped_chapters[c_name]["lessons"][l_name]["notes"]):
                    grouped_chapters[c_name]["lessons"][l_name]["notes"].append({"id": n.notes_id, "title": n.title})

    result = []
    for c_name, c_data in grouped_chapters.items():
        c_data["lessons"] = list(c_data["lessons"].values())
        result.append(c_data)
        
    return result


# Grades
@app.get('/content_management/get_grades/', response_model=List[schemas.GradeOut])
def get_grades(db: Session = Depends(get_db)):
    return db.query(models.Grade).all()

@app.post('/content_management/grades/', response_model=schemas.GradeOut)
def create_grade(grade: schemas.GradeCreate, db: Session = Depends(get_db)):
    db_grade = models.Grade(**grade.dict())
    db.add(db_grade)
    db.commit()
    db.refresh(db_grade)
    return db_grade

# Subjects
@app.get('/content_management/subjects/', response_model=List[schemas.SubjectOut])
def get_subjects_endpoint(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()

@app.get('/content_management/get_subjects/', response_model=List[schemas.SubjectOut])
def get_subjects_by_grade(grade: Optional[str] = Query(None), db: Session = Depends(get_db)):
    # Our mock subjects were global, so we return all subjects regardless of grade query
    return db.query(models.Subject).all()

@app.post('/content_management/subjects/', response_model=schemas.SubjectOut)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_subject = models.Subject(**subject.dict())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject

# Chapters
@app.get('/content_management/', response_model=List[schemas.ChapterOut])
def get_chapters(grade_id: Optional[str] = Query(None), subject_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Chapter)
    if grade_id:
        query = query.filter(models.Chapter.grade_id == grade_id)
    if subject_id:
        # Allow querying by either the UUID or the human-readable SUB00X string
        query = query.join(models.Subject).filter(
            (models.Chapter.subject_id == subject_id) | (models.Subject.subject_id == subject_id)
        )
        
    chapters = query.all()
    
    # Deduplicate by chapter_name since mock data has duplicate curriculums for School 1 and School 2
    seen = set()
    unique_chapters = []
    for c in chapters:
        name_key = c.chapter_name.strip().lower()
        if name_key not in seen:
            seen.add(name_key)
            unique_chapters.append(c)
            
    return unique_chapters

from sqlalchemy import func

@app.get('/content_management/get_latest_chapters/', response_model=List[schemas.ChapterOut])
def get_latest_chapters(db: Session = Depends(get_db)):
    chapters = db.query(models.Chapter).all()
    seen = set()
    unique_chapters = []
    for c in chapters:
        name_key = c.chapter_name.strip().lower()
        if name_key not in seen:
            seen.add(name_key)
            unique_chapters.append(c)
            if len(unique_chapters) >= 4:
                break
    return unique_chapters

from pydantic import BaseModel
class FrontendLesson(BaseModel):
    title: str
    short_description: Optional[str] = None
    long_description: Optional[str] = None

class FrontendChapterCreate(BaseModel):
    chapter_name: str
    short_description: Optional[str] = None
    grades: Optional[List[str]] = []
    subject: Optional[str] = None
    status: Optional[str] = None
    lessons: Optional[List[FrontendLesson]] = []

@app.post('/content_management/chapters/')
@app.post('/content_management/create_chapter/')
def create_chapter_frontend(payload: FrontendChapterCreate, db: Session = Depends(get_db)):
    db_chapter = models.Chapter(
        chapter_name=payload.chapter_name,
        grade_id=payload.grades[0] if payload.grades else None,
        subject_id=payload.subject if payload.subject else None
    )
    db.add(db_chapter)
    db.commit()
    db.refresh(db_chapter)
    
    for l in payload.lessons:
        lesson = models.Lesson(
            lesson_name=l.title,
            chapter_id=db_chapter.uid,
            module_content={"text": l.long_description} if l.long_description else None
        )
        db.add(lesson)
    db.commit()

    return {"status": "success", "chapter_id": db_chapter.uid}

@app.get('/content_management/{slug}/')
def get_chapter(slug: str, db: Session = Depends(get_db)):
    chapter_name_approx = slug.replace("-", " ")
    chapter = db.query(models.Chapter).filter(
        func.lower(models.Chapter.chapter_name) == chapter_name_approx
    ).first()
    
    if not chapter:
        chapter = db.query(models.Chapter).filter(models.Chapter.uid == slug).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
            
    lessons = db.query(models.Lesson).filter(models.Lesson.chapter_id == chapter.uid).all()
    
    teacher = chapter.completed_by_teacher
    created_by = {
        "id": teacher.uid if teacher else 0,
        "first_name": teacher.name.split(" ")[0] if teacher and teacher.name else "Unknown",
        "last_name": " ".join(teacher.name.split(" ")[1:]) if teacher and teacher.name else ""
    }
    
    chapter_dict = {
        "id": chapter.uid,
        "uid": chapter.uid,
        "chapter_name": chapter.chapter_name,
        "slug": slug,
        "short_description": getattr(chapter, "short_description", "No description available"),
        "created_by": created_by
    }
    
    numeric_chapter_id = extract_numeric_id(chapter.uid)
    assessment_lesson_ids = [
        a.lesson_id for a in db.query(models.AssessmentModel).filter(
            models.AssessmentModel.chapter_id == numeric_chapter_id
        ).all()
    ]
    homework_lesson_ids = [
        h.lesson_id for h in db.query(models.HomeworkModel).filter(
            models.HomeworkModel.chapter_id == numeric_chapter_id
        ).all()
    ]
    
    lessons_list = []
    for l in lessons:
        numeric_lesson_id = extract_numeric_id(l.uid)
        
        base_lesson = {
            "id": l.uid,
            "uid": l.uid,
            "title": l.lesson_name,
            "lesson_name": l.lesson_name,
            "slug": l.lesson_name.lower().replace(" ", "-") if l.lesson_name else l.uid,
            "long_description": l.module_content.get("text", "") if isinstance(l.module_content, dict) else str(l.module_content or ""),
            "short_description": "Lesson content"
        }
        
        # Always append the article version
        article_lesson = dict(base_lesson)
        article_lesson["lesson_type"] = "article"
        lessons_list.append(article_lesson)
        
        # Append a quiz version if it has an assessment
        if numeric_lesson_id in assessment_lesson_ids:
            quiz_lesson = dict(base_lesson)
            quiz_lesson["lesson_type"] = "quiz"
            quiz_lesson["id"] = f"{base_lesson['id']}-quiz"
            quiz_lesson["uid"] = f"{base_lesson['uid']}-quiz"
            lessons_list.append(quiz_lesson)
            
        # Append a homework version if it has homework
        if numeric_lesson_id in homework_lesson_ids:
            hw_lesson = dict(base_lesson)
            hw_lesson["lesson_type"] = "homework"
            hw_lesson["id"] = f"{base_lesson['id']}-homework"
            hw_lesson["uid"] = f"{base_lesson['uid']}-homework"
            lessons_list.append(hw_lesson)
    
    return {
        "chapter": chapter_dict,
        "lessons": lessons_list
    }

# --- Activities & Lesson Extras ---



@app.post('/activities/track_started/{slug}/{lesson_slug}/')
def track_started(slug: str, lesson_slug: str):
    return {"status": "started"}

@app.get('/activities/get_active_chapters/')
def get_active_chapters():
    return []

@app.post('/activities/mark_as_done/{slug}/{lesson_slug}/')
def mark_as_done(slug: str, lesson_slug: str):
    return {"status": "completed"}

@app.get('/content_management/{slug}/{lesson_slug}/get-quiz/')
def get_quiz(slug: str, lesson_slug: str, db: Session = Depends(get_db)):
    lesson_name_approx = lesson_slug.replace("-", " ")
    lesson = db.query(models.Lesson).filter(func.lower(models.Lesson.lesson_name) == lesson_name_approx).first()
    if not lesson:
        lesson = db.query(models.Lesson).filter(models.Lesson.uid == lesson_slug).first()
        
    assessment = None
    if lesson:
        numeric_lesson_id = extract_numeric_id(lesson.uid)
        
        assessment = db.query(models.AssessmentModel).filter(
            models.AssessmentModel.lesson_id == numeric_lesson_id
        ).first()
        
    if not assessment:
        assessment = db.query(models.AssessmentModel).first()
        
    if not assessment:
        return []
        
    mcq_pool = assessment.mcq_pool if assessment.mcq_pool else []
    answers_pool = assessment.answers_pool if assessment.answers_pool else []
    
    formatted_quiz = []
    
    answers_map = {ans.get("question", ""): ans.get("answer", "") for ans in answers_pool if isinstance(ans, dict)}
    
    if isinstance(mcq_pool, list):
        for idx, mcq in enumerate(mcq_pool):
            question = mcq.get("question", "")
            options = mcq.get("options", [])
            correct_answer = mcq.get("correct_answer", answers_map.get(question, ""))
            
            formatted_quiz.append({
                "id": f"q{idx + 1}",
                "question": question,
                "options": options,
                "answer": correct_answer
            })
            
    return formatted_quiz


@app.get('/content_management/get_author_chapters/{id}/')
def get_author_chapters(id: str, db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.uid == id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    chapters = db.query(models.Chapter).filter(models.Chapter.completed_by == id).all()
    return {
        "created_by": {
            "id": teacher.uid,
            "first_name": teacher.name.split(" ")[0] if teacher.name else "",
            "last_name": " ".join(teacher.name.split(" ")[1:]) if teacher.name else ""
        },
        "chapters": [
            {
                "id": c.uid,
                "chapter_name": c.chapter_name,
                "grade": c.grade.uid if c.grade else None,
                "subject": c.subject.subject_name if c.subject else None,
            } for c in chapters
        ]
    }

# Lessons
@app.get('/content_management/lessons/', response_model=List[schemas.LessonOut])
def get_lessons(db: Session = Depends(get_db)):
    return db.query(models.Lesson).all()

@app.post('/content_management/lessons/', response_model=schemas.LessonOut)
def create_lesson(lesson: schemas.LessonCreate, db: Session = Depends(get_db)):
    db_lesson = models.Lesson(**lesson.dict())
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson
