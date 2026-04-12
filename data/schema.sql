-- ============================================================
-- CourseWeave AI — Complete Database Schema
-- PostgreSQL 14+
-- Matches live GCP VM (34.23.27.68) as of April 2026
-- ============================================================
-- Usage (fresh setup on a new machine):
--   1. psql -h <host> -U courseweave_user -d courseweave -f data/schema.sql
--   2. psql -h <host> -U courseweave_user -d courseweave -f data/Seed_data.pgsql
--
-- DO NOT run against the live GCP VM — schema already exists there.
-- ============================================================


-- ============================================================
-- COURSE CATALOG
-- ============================================================

CREATE TABLE IF NOT EXISTS courses (
    id           SERIAL PRIMARY KEY,
    course_code  VARCHAR(20) UNIQUE NOT NULL,
    course_name  TEXT        NOT NULL,
    credits      INTEGER     NOT NULL,
    program_code VARCHAR(20) NOT NULL,           -- MS_DAE | MS_CS | MS_DS | MS_DA | MS_IS
    course_type  VARCHAR(20) NOT NULL,           -- Core | Elective
    is_active    BOOLEAN     DEFAULT TRUE,
    created_at   TIMESTAMP   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prerequisites (
    id                   SERIAL PRIMARY KEY,
    course_code          VARCHAR(20) NOT NULL REFERENCES courses(course_code),
    required_course_code VARCHAR(20) NOT NULL REFERENCES courses(course_code),
    UNIQUE(course_code, required_course_code)
);


-- ============================================================
-- PROGRAM REQUIREMENTS
-- Queried by get_degree_audit() in postgres_filter.py
-- ============================================================

CREATE TABLE IF NOT EXISTS program_requirements (
    id                       SERIAL PRIMARY KEY,
    program_code             VARCHAR(20) UNIQUE NOT NULL,
    program_name             TEXT        NOT NULL,
    total_credits            INTEGER     NOT NULL,
    core_credits             INTEGER     NOT NULL,
    elective_credits         INTEGER     NOT NULL,   -- coursework path
    project_available        BOOLEAN     DEFAULT TRUE,
    project_credits          INTEGER     DEFAULT 4,
    project_elective_credits INTEGER     DEFAULT 8,  -- elective credits on project path
    thesis_available         BOOLEAN     DEFAULT FALSE,
    thesis_credits           INTEGER     DEFAULT 0,
    thesis_elective_credits  INTEGER     DEFAULT 0,  -- elective credits on thesis path
    min_gpa                  NUMERIC(3,2) DEFAULT 3.0,
    catalog_url              TEXT,
    notes                    TEXT,
    created_at               TIMESTAMP   DEFAULT NOW()
);


-- ============================================================
-- STUDENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS students (
    id               SERIAL PRIMARY KEY,
    name             TEXT        NOT NULL,
    email            TEXT UNIQUE NOT NULL,
    program_code     VARCHAR(20) NOT NULL,
    target_career    VARCHAR(100),                   -- Data Engineer | Data Scientist | etc.
    created_at       TIMESTAMP   DEFAULT NOW(),
    degree_path      VARCHAR(20) DEFAULT 'undecided', -- undecided | coursework | project | thesis
    path_selected_at TIMESTAMP,
    password_hash    TEXT
);

CREATE TABLE IF NOT EXISTS student_courses (
    id           SERIAL PRIMARY KEY,
    student_id   INTEGER NOT NULL REFERENCES students(id),
    course_code  VARCHAR(20) NOT NULL REFERENCES courses(course_code),
    completed_at DATE    NOT NULL,
    grade        VARCHAR(5),
    UNIQUE(student_id, course_code)
);


-- ============================================================
-- CONVERSATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS conversations (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title           TEXT    NOT NULL DEFAULT 'New Chat',
    session_context JSONB,           -- cached RAG context: courses, prereq_status, career_goal, career_skills
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_student ON conversations(student_id);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER     NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL CHECK (role IN ('user', 'model')),
    text            TEXT        NOT NULL,
    courses         JSONB       DEFAULT '[]',
    action          VARCHAR(20),                 -- recommend | followup | ask_path | complete
    created_at      TIMESTAMP   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_messages_conv ON conversation_messages(conversation_id);


-- ============================================================
-- PROGRAM REQUIREMENTS SEED DATA
-- Source: NEU graduate catalog (verified against live VM)
-- ============================================================

INSERT INTO program_requirements
    (program_code, program_name, total_credits, core_credits, elective_credits,
     project_available, project_credits, project_elective_credits,
     thesis_available, thesis_credits, thesis_elective_credits,
     min_gpa, catalog_url, notes)
VALUES
    (
        'MS_DAE',
        'Data Analytics Engineering, MS (Boston)',
        32, 20, 12,
        TRUE, 4, 8,
        TRUE, 4, 4,
        3.00,
        'https://catalog.northeastern.edu/graduate/engineering/mechanical-industrial/data-analytics-engineering-ms/',
        'Core: IE6400 IE6700 IE7275 IE6600 IE6200. Project course: IE7945. Three paths: coursework/project/thesis.'
    ),
    (
        'MS_DS',
        'Master of Science in Data Science',
        32, 16, 16,
        TRUE, 4, 12,
        TRUE, 4, 12,
        3.00,
        'https://catalog.northeastern.edu/graduate/university-interdisciplinary-programs/science-data-ms-bos/',
        'Core: DS5110 DS5220 DS5230 DS5500. Jointly Khoury + Engineering.'
    ),
    (
        'MS_CS',
        'Master of Science in Computer Science',
        32, 8, 24,
        TRUE, 4, 20,
        TRUE, 4, 20,
        3.00,
        'https://catalog.northeastern.edu/graduate/computer-information-science/computer-science/computer-science-mscs/',
        'Core: CS6140 + 1 other. Highly elective-driven program.'
    ),
    (
        'MS_DA',
        'Master of Science in Data Analytics',
        32, 16, 16,
        TRUE, 4, 12,
        FALSE, 0, 0,
        3.00,
        'https://catalog.northeastern.edu/graduate/business/',
        'Business-focused analytics. D''Amore-McKim School of Business.'
    ),
    (
        'MS_IS',
        'Master of Science in Information Systems',
        32, 16, 16,
        TRUE, 4, 12,
        FALSE, 0, 0,
        3.00,
        'https://catalog.northeastern.edu/graduate/computer-information-science/',
        'Information Systems program.'
    )
ON CONFLICT (program_code) DO NOTHING;