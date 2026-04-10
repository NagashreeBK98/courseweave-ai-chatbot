from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import psycopg2
import psycopg2.extras
import jwt
import bcrypt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="CourseWeave AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "courseweave-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

security = HTTPBearer()

PROGRAMS = ["MS_DAE", "MS_DS", "MS_CS", "MS_DA", "MS_IS"]
CAREERS = ["Data Engineer", "Data Scientist", "Data Analyst", "Business Analyst", "Software Engineer", "ML Engineer"]


def get_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "34.23.27.68"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "courseweave"),
        user=os.getenv("DB_USER", "courseweave_user"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    conn.autocommit = True
    return conn


def create_token(student_id: int, email: str) -> str:
    payload = {
        "sub": str(student_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"student_id": int(payload["sub"]), "email": payload["email"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Pydantic models ──────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    program_code: str
    target_career: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RecommendRequest(BaseModel):
    career_goal: Optional[str] = None

class AddCourseRequest(BaseModel):
    course_code: str
    grade: str
    completed_at: str


# ── Auth endpoints ───────────────────────────────────────────────────────────

@app.post("/auth/signup")
def signup(req: SignupRequest):
    if req.program_code not in PROGRAMS:
        raise HTTPException(400, detail=f"Invalid program. Choose from {PROGRAMS}")
    if req.target_career not in CAREERS:
        raise HTTPException(400, detail=f"Invalid career. Choose from {CAREERS}")

    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO students (name, email, program_code, target_career, password_hash) VALUES (%s,%s,%s,%s,%s) RETURNING id, name, email, program_code, target_career",
            (req.name, req.email, req.program_code, req.target_career, hashed),
        )
        student = dict(cur.result() if hasattr(cur, 'result') else cur.fetchone())
        conn.close()
        token = create_token(student["id"], student["email"])
        return {"token": token, "student": student}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, detail="Email already registered")
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM students WHERE email = %s", (req.email,))
        row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(401, detail="Invalid credentials")
        student = dict(row)
        pw_hash = student.get("password_hash", "")
        if not pw_hash or not bcrypt.checkpw(req.password.encode(), pw_hash.encode()):
            raise HTTPException(401, detail="Invalid credentials")
        token = create_token(student["id"], student["email"])
        student.pop("password_hash", None)
        return {"token": token, "student": student}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/auth/me")
def me(user=Depends(verify_token)):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, name, email, program_code, target_career, created_at FROM students WHERE id = %s",
            (user["student_id"],),
        )
        student = dict(cur.fetchone())
        conn.close()
        return student
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Student dashboard ────────────────────────────────────────────────────────

@app.get("/student/dashboard")
def dashboard(user=Depends(verify_token)):
    sid = user["student_id"]
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute(
            """SELECT s.id, s.name, s.email, s.program_code, s.target_career
               FROM students s WHERE s.id = %s""",
            (sid,),
        )
        student = dict(cur.fetchone())

        cur.execute(
            """SELECT sc.course_code, c.course_name, c.credits, c.course_type,
                      sc.grade, sc.completed_at
               FROM student_courses sc
               JOIN courses c ON c.course_code = sc.course_code
               WHERE sc.student_id = %s
               ORDER BY sc.completed_at DESC""",
            (sid,),
        )
        completed = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT c.course_code, c.course_name, c.credits, c.course_type, c.program_code
               FROM courses c
               WHERE c.program_code = %s AND c.is_active = TRUE
               AND c.course_code NOT IN (
                   SELECT course_code FROM student_courses WHERE student_id = %s
               )""",
            (student["program_code"], sid),
        )
        remaining = [dict(r) for r in cur.fetchall()]

        prog_map = {
            "MS_DAE": 40, "MS_DS": 40, "MS_CS": 40, "MS_DA": 40, "MS_IS": 40
        }
        total_required = prog_map.get(student["program_code"], 40)
        credits_done = sum(c["credits"] for c in completed)
        credits_remaining = total_required - credits_done

        core_done = sum(1 for c in completed if c["course_type"] == "Core")
        elective_done = sum(1 for c in completed if c["course_type"] == "Elective")

        gpa_map = {"A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7, "C+": 2.3, "C": 2.0}
        grades = [gpa_map.get(c["grade"], 0) for c in completed if c["grade"]]
        gpa = round(sum(grades) / len(grades), 2) if grades else 0.0

        conn.close()
        return {
            "student": student,
            "stats": {
                "credits_completed": credits_done,
                "credits_remaining": credits_remaining,
                "total_required": total_required,
                "progress_pct": round((credits_done / total_required) * 100),
                "courses_completed": len(completed),
                "core_completed": core_done,
                "electives_completed": elective_done,
                "gpa": gpa,
            },
            "completed_courses": completed,
            "remaining_courses": remaining,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Courses catalog ──────────────────────────────────────────────────────────

@app.get("/courses")
def get_courses(program: Optional[str] = None, course_type: Optional[str] = None, user=Depends(verify_token)):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = "SELECT * FROM courses WHERE is_active = TRUE"
        params = []
        if program:
            query += " AND program_code = %s"
            params.append(program)
        if course_type:
            query += " AND course_type = %s"
            params.append(course_type)
        query += " ORDER BY program_code, course_type, course_code"
        cur.execute(query, params)
        courses = [dict(r) for r in cur.fetchall()]
        conn.close()
        return courses
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/courses/{course_code}/prerequisites")
def get_prerequisites(course_code: str, user=Depends(verify_token)):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT p.required_course_code, c.course_name, c.credits
               FROM prerequisites p
               JOIN courses c ON c.course_code = p.required_course_code
               WHERE p.course_code = %s""",
            (course_code,),
        )
        prereqs = [dict(r) for r in cur.fetchall()]
        conn.close()
        return prereqs
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Student courses ──────────────────────────────────────────────────────────

@app.get("/student/courses")
def student_courses(user=Depends(verify_token)):
    sid = user["student_id"]
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT sc.id, sc.course_code, c.course_name, c.credits, c.course_type,
                      sc.grade, sc.completed_at
               FROM student_courses sc
               JOIN courses c ON c.course_code = sc.course_code
               WHERE sc.student_id = %s
               ORDER BY sc.completed_at DESC""",
            (sid,),
        )
        courses = [dict(r) for r in cur.fetchall()]
        conn.close()
        return courses
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/student/courses")
def add_course(req: AddCourseRequest, user=Depends(verify_token)):
    sid = user["student_id"]
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO student_courses (student_id, course_code, grade, completed_at) VALUES (%s,%s,%s,%s) RETURNING *",
            (sid, req.course_code, req.grade, req.completed_at),
        )
        row = dict(cur.fetchone())
        conn.close()
        return row
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, detail="Course already added")
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Prerequisites checker ────────────────────────────────────────────────────

@app.get("/student/prerequisites")
def check_prerequisites(user=Depends(verify_token)):
    sid = user["student_id"]
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT course_code FROM student_courses WHERE student_id = %s", (sid,))
        completed_codes = {r["course_code"] for r in cur.fetchall()}

        cur.execute("SELECT id, course_code FROM students WHERE id = %s", (sid,))
        student = dict(cur.fetchone())

        cur.execute(
            "SELECT course_code, course_name FROM courses WHERE program_code = (SELECT program_code FROM students WHERE id = %s) AND is_active = TRUE",
            (sid,),
        )
        all_courses = [dict(r) for r in cur.fetchall()]

        result = []
        for course in all_courses:
            code = course["course_code"]
            cur.execute(
                """SELECT p.required_course_code, c.course_name
                   FROM prerequisites p JOIN courses c ON c.course_code = p.required_course_code
                   WHERE p.course_code = %s""",
                (code,),
            )
            prereqs = [dict(r) for r in cur.fetchall()]
            if not prereqs:
                continue
            missing = [p for p in prereqs if p["required_course_code"] not in completed_codes]
            result.append({
                "course_code": code,
                "course_name": course["course_name"],
                "prerequisites": prereqs,
                "missing_prerequisites": missing,
                "eligible": len(missing) == 0,
                "completed": code in completed_codes,
            })

        conn.close()
        return result
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Recommendations ──────────────────────────────────────────────────────────

@app.post("/recommend")
def recommend(req: RecommendRequest, user=Depends(verify_token)):
    sid = user["student_id"]
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        from src.agents.recommendation_agent import RecommendationAgent

        agent = RecommendationAgent()
        result = agent.recommend(student_id=sid)
        return {"recommendations": result, "source": "rag"}
    except ImportError:
        return _fallback_recommend(sid)
    except Exception as e:
        return _fallback_recommend(sid)


def _fallback_recommend(student_id: int):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT c.course_code, c.course_name, c.credits, c.course_type
               FROM courses c
               WHERE c.program_code = (SELECT program_code FROM students WHERE id = %s)
               AND c.is_active = TRUE
               AND c.course_code NOT IN (SELECT course_code FROM student_courses WHERE student_id = %s)
               LIMIT 5""",
            (student_id, student_id),
        )
        courses = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {
            "recommendations": [
                {**c, "reason": "Recommended based on your program and remaining requirements"}
                for c in courses
            ],
            "source": "fallback",
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Roadmap ──────────────────────────────────────────────────────────────────

@app.get("/student/roadmap")
def roadmap(user=Depends(verify_token)):
    sid = user["student_id"]
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute(
            """SELECT sc.course_code, c.course_name, c.credits, c.course_type,
                      sc.grade, sc.completed_at
               FROM student_courses sc JOIN courses c ON c.course_code = sc.course_code
               WHERE sc.student_id = %s ORDER BY sc.completed_at""",
            (sid,),
        )
        completed = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT c.course_code, c.course_name, c.credits, c.course_type
               FROM courses c
               WHERE c.program_code = (SELECT program_code FROM students WHERE id = %s)
               AND c.is_active = TRUE
               AND c.course_code NOT IN (SELECT course_code FROM student_courses WHERE student_id = %s)
               ORDER BY c.course_type, c.course_code""",
            (sid, sid),
        )
        remaining = [dict(r) for r in cur.fetchall()]
        conn.close()

        semesters = []
        if completed:
            dates = {}
            for c in completed:
                key = str(c["completed_at"])
                if key not in dates:
                    dates[key] = []
                dates[key].append(c)
            for i, (date, courses) in enumerate(sorted(dates.items()), 1):
                semesters.append({"label": f"Semester {i}", "status": "completed", "courses": courses})

        chunk = 3
        for i in range(0, len(remaining), chunk):
            sem_num = len(semesters) + 1
            status = "current" if i == 0 else "planned"
            semesters.append({
                "label": f"Semester {sem_num}",
                "status": status,
                "courses": remaining[i:i + chunk],
            })

        return {"semesters": semesters}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "service": "CourseWeave AI API"}
