import { useEffect, useState, useCallback } from 'react'
import { studentApi, coursesApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { Badge, PageSpinner, PageHeader, Alert } from '../components/ui'
import { CheckCircle2, Circle, Clock, Plus, Pencil, Trash2, X } from 'lucide-react'
import styles from './RoadmapPage.module.css'

const statusIcon  = { completed: CheckCircle2, current: Clock, planned: Circle }
const statusColor = { completed: 'var(--success)', current: 'var(--accent)', planned: 'var(--border-strong)' }
const GRADES      = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-']

// ── Unified add / edit modal ────────────────────────────────────────────────
function CourseModal({ mode, initial, programCode, completedCodes, onClose, onSave }) {
  const [courses, setCourses] = useState([])
  const [form,    setForm]    = useState({
    course_code:  initial?.course_code  || '',
    grade:        initial?.grade        || '',
    completed_at: initial?.completed_at || '',
  })
  const [saving, setSaving] = useState(false)
  const [error,  setError]  = useState('')

  useEffect(() => {
    coursesApi.list({ program: programCode }).then(r => {
      const eligible = r.data.filter(c =>
        !completedCodes.has(c.course_code) || c.course_code === initial?.course_code
      )
      setCourses(eligible)
    })
  }, [])

  const handle = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    if (!form.course_code) { setError('Please select a course.'); return }
    setSaving(true); setError('')
    try {
      if (mode === 'edit' && initial?.course_code) {
        await studentApi.removeCourse(initial.course_code)
      }
      await studentApi.addCourse(form)
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save.')
      setSaving(false)
    }
  }

  const core           = courses.filter(c => c.course_type === 'Core')
  const electives      = courses.filter(c => c.course_type === 'Elective')
  const selectedCourse = courses.find(c => c.course_code === form.course_code)

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>
            {mode === 'edit' ? 'Edit Course' : 'Add Course'}
          </h2>
          <button className={styles.modalClose} onClick={onClose}><X size={16} /></button>
        </div>

        <form onSubmit={submit} className={styles.modalForm}>
          {/* Course dropdown */}
          <div className={styles.modalField}>
            <label>Course</label>
            <select name="course_code" value={form.course_code} onChange={handle} required>
              <option value="">Select a course…</option>
              {core.length > 0 && (
                <optgroup label="── Core courses">
                  {core.map(c => (
                    <option key={c.course_code} value={c.course_code}>
                      {c.course_code} — {c.course_name} ({c.credits} cr)
                    </option>
                  ))}
                </optgroup>
              )}
              {electives.length > 0 && (
                <optgroup label="── Elective courses">
                  {electives.map(c => (
                    <option key={c.course_code} value={c.course_code}>
                      {c.course_code} — {c.course_name} ({c.credits} cr)
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          {/* Credits — auto-filled from selected course */}
          <div className={styles.modalField}>
            <label>Credits</label>
            <select disabled>
              <option>
                {selectedCourse ? `${selectedCourse.credits} credits` : 'Select a course first…'}
              </option>
            </select>
          </div>

          {/* Grade and date */}
          <div className={styles.modalRow}>
            <div className={styles.modalField}>
              <label>Grade</label>
              {mode === 'add' ? (
                <div className={styles.lockedField}>Yet to be Graded</div>
              ) : (
                <select name="grade" value={form.grade} onChange={handle}>
                  <option value="">Yet to be Graded</option>
                  {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              )}
            </div>
            <div className={styles.modalField}>
              <label>Completion date</label>
              {mode === 'add' ? (
                <div className={styles.lockedField}>mm/dd/yyyy</div>
              ) : (
                <input type="date" name="completed_at" value={form.completed_at} onChange={handle} />
              )}
            </div>
          </div>

          {error && <p className={styles.modalError}>{error}</p>}

          <button type="submit" className={styles.modalSubmit} disabled={saving}>
            {saving ? 'Saving…' : mode === 'edit' ? 'Save changes' : 'Add course'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────
export default function RoadmapPage() {
  const { student }                   = useAuth()
  const [data,      setData]          = useState(null)
  const [loading,   setLoading]       = useState(true)
  const [error,     setError]         = useState('')
  const [modalInfo, setModalInfo]     = useState(null)   // { mode, initial } | null
  const [deleting,  setDeleting]      = useState(null)   // course_code being deleted

  const loadRoadmap = useCallback(() => {
    setLoading(true)
    studentApi.roadmap()
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load roadmap.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadRoadmap() }, [loadRoadmap])

  if (loading) return <PageSpinner />
  if (error)   return <Alert type="danger">{error}</Alert>

  const { semesters, summary } = data

  // Exclude both completed AND temp-planned courses from the add dropdown
  const completedCodes = new Set(
    semesters
      .filter(s => s.status === 'completed' || s.status === 'current')
      .flatMap(s => s.courses.map(c => c.course_code))
  )

  const openAdd  = ()       => setModalInfo({ mode: 'add',  initial: null })
  const openEdit = (course) => setModalInfo({ mode: 'edit', initial: course })

  const handleDelete = async (courseCode) => {
    setDeleting(courseCode)
    try {
      await studentApi.removeCourse(courseCode)
      loadRoadmap()
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="fade-in">
      <PageHeader title="My Roadmap" subtitle="Your semester-by-semester academic journey" />

      {summary && (
        <div className={styles.summaryBar}>
          <span>{summary.credits_total_used} / {summary.total_credits} credits used</span>
          <span className={styles.summaryDivider}>·</span>
          <span>{summary.credits_remaining} credits remaining</span>
          <span className={styles.summaryDivider}>·</span>
          <span>{summary.core_credits_remaining} core · {summary.elective_credits_remaining} elective left</span>
        </div>
      )}

      <div className={styles.timeline}>
        {semesters.map((sem, idx) => {
          const Icon         = statusIcon[sem.status]
          const color        = statusColor[sem.status]
          const totalCredits = sem.courses.reduce((s, c) => s + (c.credits || 0), 0)
          const slotCount    = sem.courses.length || 3
          const atLimit      = summary && summary.credits_remaining === 0

          // Reusable chip renderer
          const renderChip = (c) => (
            <div key={c.course_code} className={`${styles.courseChip} ${styles[`chip_${sem.status}`]}`}>
              <div className={styles.chipActions}>
                <button
                  className={styles.chipBtn}
                  title="Edit"
                  onClick={() => openEdit({ course_code: c.course_code, grade: c.grade, completed_at: c.completed_at })}
                >
                  <Pencil size={11} />
                </button>
                <button
                  className={`${styles.chipBtn} ${styles.chipBtnDanger}`}
                  title="Remove"
                  disabled={deleting === c.course_code}
                  onClick={() => handleDelete(c.course_code)}
                >
                  <Trash2 size={11} />
                </button>
              </div>
              <div className={styles.chipTop}>
                <span className={styles.chipCode}>{c.course_code}</span>
                <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
                {c.grade
                  ? <Badge variant="success">{c.grade}</Badge>
                  : <span className={styles.chipPending}>Yet to be graded</span>
                }
              </div>
              <p className={styles.chipName}>{c.course_name}</p>
              <p className={styles.chipCredits}>{c.credits} credits</p>
              <p className={styles.chipDate}>
                {c.completed_at
                  ? new Date(c.completed_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
                  : <span className={styles.chipPending}>Yet to be completed</span>
                }
              </p>
            </div>
          )

          const addSlot = (
            <button
              key="add"
              className={`${styles.emptySlot} ${atLimit ? styles.emptySlotDisabled : ''}`}
              onClick={atLimit ? undefined : openAdd}
              title={atLimit ? `Maximum ${summary?.total_credits} credits reached` : 'Add course'}
              disabled={atLimit}
            >
              <Plus size={18} className={styles.emptySlotIcon} />
              <span className={styles.emptySlotLabel}>{atLimit ? 'Credit limit reached' : 'Add course'}</span>
            </button>
          )

          return (
            <div key={idx} className={`${styles.semBlock} ${styles[sem.status]}`}>
              <div className={styles.semHead}>
                <div className={styles.semIconWrap}>
                  <Icon size={20} color={color} strokeWidth={1.8} />
                  {idx < semesters.length - 1 && <div className={styles.connector} />}
                </div>
                <div className={styles.semInfo}>
                  <div className={styles.semLabel}>{sem.label}</div>
                  <div className={styles.semMeta}>
                    {sem.status === 'completed' ? (
                      <>{sem.courses.length} courses · {totalCredits} credits <span className={styles.completedTag}>Completed</span></>
                    ) : sem.status === 'current' ? (
                      <>{sem.courses.length > 0 && <>{sem.courses.length} courses · {totalCredits} credits · </>}<span className={styles.currentTag}>Current semester</span></>
                    ) : (
                      <span className={styles.plannedTag}>Planned</span>
                    )}
                  </div>
                </div>
              </div>

              <div className={styles.courseGrid}>
                {sem.status === 'completed' ? (
                  // Completed: chips only, no add button
                  sem.courses.map(renderChip)
                ) : sem.status === 'current' ? (
                  // Current: existing chips + add slot (max 3 courses per semester)
                  <>{sem.courses.map(renderChip)}{sem.courses.length < 3 && addSlot}</>
                ) : (
                  // Planned: all empty slots
                  Array.from({ length: slotCount }).map((_, i) => (
                    <button
                      key={i}
                      className={`${styles.emptySlot} ${atLimit ? styles.emptySlotDisabled : ''}`}
                      onClick={atLimit ? undefined : openAdd}
                      disabled={atLimit}
                    >
                      <Plus size={18} className={styles.emptySlotIcon} />
                      <span className={styles.emptySlotLabel}>{atLimit ? 'Credit limit reached' : 'Add course'}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )
        })}

        {semesters.length === 0 && (
          <div className={styles.emptyState}>
            <p>No courses recorded yet.</p>
            <button className={styles.addFirstBtn} onClick={openAdd}>
              <Plus size={14} /> Add your first course
            </button>
          </div>
        )}
      </div>

      {modalInfo && (
        <CourseModal
          mode={modalInfo.mode}
          initial={modalInfo.initial}
          programCode={student?.program_code}
          completedCodes={completedCodes}
          onClose={() => setModalInfo(null)}
          onSave={() => { setModalInfo(null); loadRoadmap() }}
        />
      )}
    </div>
  )
}
