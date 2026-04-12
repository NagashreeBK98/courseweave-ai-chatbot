import { useState, useEffect } from 'react'
import { X, Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { studentApi, coursesApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import styles from './AcademicProfileModal.module.css'

const INTAKE_MONTHS = ['Jan', 'May', 'Sep']
const ALL_MONTHS    = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const INTAKE_YEARS  = [2022, 2023, 2024, 2025, 2026]
const GRAD_YEARS    = [2024, 2025, 2026, 2027, 2028]
const GRADES        = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'W', 'IP']
const SEM_ORDER     = ['Spring', 'Summer', 'Fall']

function nextSemester(semType, year) {
  const idx = SEM_ORDER.indexOf(semType)
  if (idx === SEM_ORDER.length - 1) return [SEM_ORDER[0], year + 1]
  return [SEM_ORDER[idx + 1], year]
}

function prevNonSummerSemester(semType, year) {
  // Go back one non-summer semester: Fall→Spring, Spring→Fall (prev year)
  if (semType === 'Fall')   return ['Spring', year]
  if (semType === 'Spring') return ['Fall',   year - 1]
  if (semType === 'Summer') return ['Spring', year]
  return ['Spring', year]
}

/**
 * Generate completed semesters from intake up to (but not including) planning semester.
 * Skips Summer by default unless includeSummer=true.
 * A typical MS is Fall→Spring (2 sems per year).
 */
function generatePastSemesters(intakeMonth, intakeYear, planningSemester, includeSummer = false) {
  const monthMap = {
    Jan: 'Spring', Feb: 'Spring', Mar: 'Spring', Apr: 'Spring',
    May: 'Summer', Jun: 'Summer', Jul: 'Summer', Aug: 'Summer',
    Sep: 'Fall',   Oct: 'Fall',   Nov: 'Fall',   Dec: 'Fall',
  }
  if (!intakeMonth || !intakeYear || !planningSemester) return []

  let semType = monthMap[intakeMonth] || 'Fall'
  let year    = parseInt(intakeYear)
  const [planType, planYearStr] = planningSemester.split(' ')
  const planYear = parseInt(planYearStr)
  const sems = []

  for (let i = 0; i < 16; i++) {
    // Stop before planning semester
    if (semType === planType && year === planYear) break
    // Safety: don't go past planning year
    if (year > planYear) break

    if (semType !== 'Summer' || includeSummer) {
      sems.push(`${semType} ${year}`)
    }
    ;[semType, year] = nextSemester(semType, year)
  }
  return sems
}

/**
 * Generate planning semester options: all Fall+Spring semesters
 * from intake+1 semester up to intake+4 years.
 */
function generatePlanningOptions(intakeMonth, intakeYear) {
  const monthMap = {
    Jan: 'Spring', May: 'Summer', Sep: 'Fall',
    Feb: 'Spring', Mar: 'Spring', Apr: 'Spring',
    Jun: 'Summer', Jul: 'Summer', Aug: 'Summer',
    Oct: 'Fall',   Nov: 'Fall',   Dec: 'Fall',
  }
  if (!intakeMonth || !intakeYear) return []

  let semType = monthMap[intakeMonth] || 'Fall'
  let year    = parseInt(intakeYear)
  const options = []

  for (let i = 0; i < 14; i++) {
    ;[semType, year] = nextSemester(semType, year)
    if (semType !== 'Summer') options.push(`${semType} ${year}`)
  }
  return options
}

export default function AcademicProfileModal({ onClose, onSubmit }) {
  const { student } = useAuth()

  const [form, setForm] = useState({
    intakeMonth:      'Sep',
    intakeYear:       '2024',
    gradMonth:        'May',
    gradYear:         '2026',
    planningSemester: '',
    gpa:              '',
  })
  const [includeSummer, setIncludeSummer]     = useState(false)
  const [semesterCourses, setSemesterCourses] = useState({})
  const [showManual, setShowManual]           = useState(false)
  const [manualCourses, setManualCourses]     = useState([])
  const [manualEntry, setManualEntry]         = useState({ course_code: '', course_name: '', credits: '4', grade: 'A' })
  const [programCourses, setProgramCourses]   = useState([])
  const [submitting, setSubmitting]           = useState(false)
  const [error, setError]                     = useState('')

  // Derived
  const planningOptions = generatePlanningOptions(form.intakeMonth, form.intakeYear)
  const pastSemesters   = generatePastSemesters(form.intakeMonth, form.intakeYear, form.planningSemester, includeSummer)

  // Pre-populate from saved profile
  useEffect(() => {
    studentApi.getProfile().then(r => {
      const p = r.data
      if (!p) return
      setForm(prev => ({
        intakeMonth:      p.intake_month      || prev.intakeMonth,
        intakeYear:       p.intake_year       ? String(p.intake_year)  : prev.intakeYear,
        gradMonth:        p.grad_month        || prev.gradMonth,
        gradYear:         p.grad_year         ? String(p.grad_year)    : prev.gradYear,
        planningSemester: p.planning_semester || prev.planningSemester,
        gpa:              p.manual_gpa        != null ? String(p.manual_gpa) : '',
      }))
    }).catch(() => {})
  }, [])

  // Re-initialise semester rows when intake/planning changes
  useEffect(() => {
    if (pastSemesters.length === 0) return
    setSemesterCourses(prev => {
      const next = {}
      pastSemesters.forEach(sem => {
        next[sem] = prev[sem] || [{ course_code: '', grade: 'A' }]
      })
      return next
    })
  }, [form.intakeMonth, form.intakeYear, form.planningSemester, includeSummer])

  // Load courses for program
  useEffect(() => {
    if (!student?.program_code) return
    coursesApi.list({ program: student.program_code })
      .then(r => setProgramCourses(r.data))
      .catch(() => {})
  }, [student])

  function setField(key, val) { setForm(p => ({ ...p, [key]: val })) }

  function addRow(sem) {
    setSemesterCourses(p => ({ ...p, [sem]: [...(p[sem] || []), { course_code: '', grade: 'A' }] }))
  }
  function updateRow(sem, idx, key, val) {
    setSemesterCourses(p => {
      const rows = [...(p[sem] || [])]
      rows[idx] = { ...rows[idx], [key]: val }
      return { ...p, [sem]: rows }
    })
  }
  function removeRow(sem, idx) {
    setSemesterCourses(p => ({ ...p, [sem]: (p[sem] || []).filter((_, i) => i !== idx) }))
  }
  function addManual() {
    if (!manualEntry.course_code.trim()) return
    setManualCourses(p => [...p, { ...manualEntry }])
    setManualEntry({ course_code: '', course_name: '', credits: '4', grade: 'A' })
  }

  async function handleSubmit() {
    if (!form.planningSemester) {
      setError('Please select the semester you are planning courses for (★ required).')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      // Derive last completed semester as currentTerm (semester before planning)
      const [planType, planYearStr] = form.planningSemester.split(' ')
      const [prevType, prevYear] = prevNonSummerSemester(planType, parseInt(planYearStr))
      const derivedCurrentTerm = `${prevType} ${prevYear}`

      await studentApi.updateProfile({
        intake_month:      form.intakeMonth,
        intake_year:       parseInt(form.intakeYear),
        grad_month:        form.gradMonth,
        grad_year:         parseInt(form.gradYear),
        current_term:      derivedCurrentTerm,
        planning_semester: form.planningSemester,
        manual_gpa:        form.gpa ? parseFloat(form.gpa) : null,
      })

      const allCourses = []
      Object.entries(semesterCourses).forEach(([sem, rows]) => {
        rows.forEach(r => {
          if (r.course_code) allCourses.push({ course_code: r.course_code, grade: r.grade, semester: sem })
        })
      })
      manualCourses.forEach(c => {
        allCourses.push({
          course_code: c.course_code, course_name: c.course_name,
          credits: parseInt(c.credits), grade: c.grade, semester: derivedCurrentTerm,
        })
      })

      if (allCourses.length > 0) await studentApi.addCoursesBatch({ courses: allCourses })

      // Notify parent — this closes the modal and starts background recommendation fetch
      onSubmit(form.planningSemester)
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>

        {/* ── Header ── */}
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>Setup Academic Profile</h2>
            <p className={styles.subtitle}>Personalise your course recommendations</p>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className={styles.body}>

          {/* ── Section 1: Timeline ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Academic Timeline</h3>

            <div className={styles.row2}>
              <div className={styles.field}>
                <label className={styles.label}>Intake Month</label>
                <select className={styles.select} value={form.intakeMonth} onChange={e => setField('intakeMonth', e.target.value)}>
                  {INTAKE_MONTHS.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              <div className={styles.field}>
                <label className={styles.label}>Intake Year</label>
                <select className={styles.select} value={form.intakeYear} onChange={e => setField('intakeYear', e.target.value)}>
                  {INTAKE_YEARS.map(y => <option key={y}>{y}</option>)}
                </select>
              </div>
            </div>

            <div className={styles.row2}>
              <div className={styles.field}>
                <label className={styles.label}>Expected Graduation</label>
                <select className={styles.select} value={form.gradMonth} onChange={e => setField('gradMonth', e.target.value)}>
                  {ALL_MONTHS.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              <div className={styles.field}>
                <label className={styles.label}>&nbsp;</label>
                <select className={styles.select} value={form.gradYear} onChange={e => setField('gradYear', e.target.value)}>
                  {GRAD_YEARS.map(y => <option key={y}>{y}</option>)}
                </select>
              </div>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>GPA So Far <span className={styles.optional}>(optional)</span></label>
              <input className={styles.input} type="number" min="0" max="4" step="0.01"
                placeholder="e.g. 3.80" value={form.gpa} onChange={e => setField('gpa', e.target.value)} />
            </div>
          </section>

          {/* ── Section 2: Planning Semester (starred) ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>
              <span className={styles.star}>★</span> Planning Courses For Semester
            </h3>
            <p className={styles.hint}>Select the semester you want course recommendations for.</p>
            <div className={styles.field}>
              <select className={styles.select} value={form.planningSemester} onChange={e => setField('planningSemester', e.target.value)}>
                <option value="">Select semester…</option>
                {planningOptions.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
          </section>

          {/* ── Section 3: Completed Courses ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Completed Courses</h3>

            <div className={styles.summerToggleRow}>
              <label className={styles.toggleLabel}>
                <input type="checkbox" checked={includeSummer} onChange={e => setIncludeSummer(e.target.checked)} />
                Include Summer semester
              </label>
              {pastSemesters.length > 0 && (
                <span className={styles.semCount}>{pastSemesters.length} semester{pastSemesters.length !== 1 ? 's' : ''} to fill</span>
              )}
            </div>

            {!form.planningSemester && (
              <p className={styles.emptyHint}>Select your planning semester above to see completed semesters.</p>
            )}

            {pastSemesters.map((sem, sIdx) => (
              <div key={sem} className={styles.semGroup}>
                <div className={styles.semLabel}>Semester {sIdx + 1} — {sem}</div>

                {(semesterCourses[sem] || []).map((row, rIdx) => (
                  <div key={rIdx} className={styles.courseRow}>
                    <select
                      className={`${styles.select} ${styles.courseSelect}`}
                      value={row.course_code}
                      onChange={e => updateRow(sem, rIdx, 'course_code', e.target.value)}
                    >
                      <option value="">Select course…</option>
                      {programCourses.map(c => (
                        <option key={c.course_code} value={c.course_code}>
                          {c.course_code} — {c.course_name}
                        </option>
                      ))}
                    </select>
                    <select
                      className={`${styles.select} ${styles.gradeSelect}`}
                      value={row.grade}
                      onChange={e => updateRow(sem, rIdx, 'grade', e.target.value)}
                    >
                      {GRADES.map(g => <option key={g}>{g}</option>)}
                    </select>
                    <button className={styles.iconBtn} onClick={() => removeRow(sem, rIdx)} title="Remove">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}

                <button className={styles.addRowBtn} onClick={() => addRow(sem)}>
                  <Plus size={13} /> Add course
                </button>
              </div>
            ))}

            {/* Manual entry */}
            <div className={styles.manualWrap}>
              <button className={styles.manualToggle} onClick={() => setShowManual(p => !p)}>
                {showManual ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                Course not in list? Add manually
              </button>
              {showManual && (
                <div className={styles.manualForm}>
                  <div className={styles.manualInputRow}>
                    <input className={styles.input} placeholder="Code" value={manualEntry.course_code}
                      onChange={e => setManualEntry(p => ({ ...p, course_code: e.target.value }))} />
                    <input className={`${styles.input} ${styles.flex2}`} placeholder="Course name" value={manualEntry.course_name}
                      onChange={e => setManualEntry(p => ({ ...p, course_name: e.target.value }))} />
                    <input className={`${styles.input} ${styles.crInput}`} type="number" placeholder="Cr" value={manualEntry.credits}
                      onChange={e => setManualEntry(p => ({ ...p, credits: e.target.value }))} />
                    <select className={`${styles.select} ${styles.gradeSelect}`} value={manualEntry.grade}
                      onChange={e => setManualEntry(p => ({ ...p, grade: e.target.value }))}>
                      {GRADES.map(g => <option key={g}>{g}</option>)}
                    </select>
                    <button className={styles.addBtn} onClick={addManual}><Plus size={14} /></button>
                  </div>
                  {manualCourses.map((c, i) => (
                    <div key={i} className={styles.manualAdded}>
                      <span className={styles.manualCode}>{c.course_code}</span>
                      <span className={styles.manualName}>{c.course_name}</span>
                      <span className={styles.manualMeta}>{c.credits} cr · {c.grade}</span>
                      <button className={styles.iconBtn} onClick={() => setManualCourses(p => p.filter((_, j) => j !== i))}>
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {error && <p className={styles.errorMsg}>{error}</p>}
        </div>

        {/* ── Footer ── */}
        <div className={styles.footer}>
          <button className={styles.cancelBtn} onClick={onClose} disabled={submitting}>Cancel</button>
          <button className={styles.submitBtn} onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Saving…' : '✦ Generate Recommendations'}
          </button>
        </div>

      </div>
    </div>
  )
}
