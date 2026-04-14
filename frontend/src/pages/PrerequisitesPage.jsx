import { useEffect, useState, useMemo } from 'react'
import { studentApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { PageSpinner, PageHeader, Alert, EmptyState } from '../components/ui'
import { CheckCircle2, XCircle, AlertCircle, Search, BookOpen, ChevronDown } from 'lucide-react'
import styles from './PrerequisitesPage.module.css'

const PROGRAM_LABELS = {
  MS_DAE: 'Data Analytics Eng.',
  MS_DS:  'Data Science',
  MS_CS:  'Computer Science',
  MS_DA:  'Data Analytics',
  MS_IS:  'Information Systems',
}

export default function PrerequisitesPage() {
  const { student } = useAuth()
  const [prereqData, setPrereqData]   = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState('')

  const [search, setSearch]           = useState('')
  const [typeFilter, setTypeFilter]   = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  useEffect(() => {
    setLoading(true)
    setError('')
    studentApi.prerequisites()
      .then(r => setPrereqData(r.data))
      .catch(() => setError('Failed to load prerequisites.'))
      .finally(() => setLoading(false))
  }, [])

  // prereqData already has all fields we need — use it directly
  const merged = useMemo(() => prereqData, [prereqData])

  // Summary counts
  const counts = useMemo(() => ({
    total:    merged.length,
    eligible: merged.filter(c => c.eligible && !c.completed).length,
    blocked:  merged.filter(c => !c.eligible && !c.completed).length,
    done:     merged.filter(c => c.completed).length,
  }), [merged])

  // Filtered list
  const displayed = useMemo(() => {
    const q = search.trim().toLowerCase()
    return merged.filter(c => {
      if (q && !c.course_code.toLowerCase().includes(q) && !c.course_name.toLowerCase().includes(q)) return false
      if (typeFilter !== 'all' && c.course_type !== typeFilter) return false
      if (statusFilter === 'eligible' && !(c.eligible && !c.completed)) return false
      if (statusFilter === 'blocked'  && !(!c.eligible && !c.completed)) return false
      if (statusFilter === 'done'     && !c.completed) return false
      return true
    })
  }, [merged, search, typeFilter, statusFilter])

  if (loading) return <PageSpinner />
  if (error)   return <Alert type="danger">{error}</Alert>

  return (
    <div className="fade-in">
      <PageHeader
        title="Prerequisites"
        subtitle={`Full prerequisite map for ${PROGRAM_LABELS[student?.program_code] || student?.program_code} — search any course to see what it requires`}
      />

      {/* ── Stats row ── */}
      <div className={styles.statsRow}>
        {[
          { key: 'all',      label: 'All Courses',     count: counts.total,    color: 'neutral', icon: <BookOpen size={16}/> },
          { key: 'eligible', label: 'Eligible Now',    count: counts.eligible, color: 'success', icon: <CheckCircle2 size={16}/> },
          { key: 'blocked',  label: 'Prereqs Missing', count: counts.blocked,  color: 'danger',  icon: <XCircle size={16}/> },
          { key: 'done',     label: 'Completed',       count: counts.done,     color: 'accent',  icon: <CheckCircle2 size={16}/> },
        ].map(s => (
          <button
            key={s.key}
            className={`${styles.statCard} ${styles[s.color]} ${statusFilter === s.key ? styles.activeCard : ''}`}
            onClick={() => setStatusFilter(statusFilter === s.key ? 'all' : s.key)}
          >
            <span className={styles.statIcon}>{s.icon}</span>
            <span className={styles.statNum}>{s.count}</span>
            <span className={styles.statLabel}>{s.label}</span>
          </button>
        ))}
      </div>

      {/* ── Search + filter bar ── */}
      <div className={styles.filterBar}>
        <div className={styles.searchWrap}>
          <Search size={15} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search by course code or name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button className={styles.clearBtn} onClick={() => setSearch('')}>✕</button>
          )}
        </div>

        <div className={styles.selectWrap}>
          <select
            className={styles.select}
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="Core">Core Courses</option>
            <option value="Elective">Elective Courses</option>
          </select>
          <ChevronDown size={13} className={styles.chevron} />
        </div>
      </div>

      {/* ── Results count ── */}
      <p className={styles.resultCount}>
        Showing <strong>{displayed.length}</strong> of {counts.total} courses
      </p>

      {displayed.length === 0 && (
        <EmptyState icon="🔍" title="No courses found" desc="Try a different search term or filter." />
      )}

      {/* ── Course cards ── */}
      <div className={styles.list}>
        {displayed.map(course => (
          <div
            key={course.course_code}
            className={`${styles.card} ${course.completed ? styles.cardDone : course.eligible ? styles.cardEligible : styles.cardBlocked}`}
          >
            {/* Left accent bar */}
            <div className={`${styles.accent} ${course.completed ? styles.accentDone : course.eligible ? styles.accentEligible : styles.accentBlocked}`} />

            <div className={styles.cardBody}>
              {/* Top row */}
              <div className={styles.cardTop}>
                <div className={styles.cardLeft}>
                  <span className={styles.courseCode}>{course.course_code}</span>
                  <div className={styles.courseMeta}>
                    <span className={styles.courseName}>{course.course_name}</span>
                    <div className={styles.badges}>
                      {course.credits && (
                        <span className={styles.badge}>{course.credits} cr</span>
                      )}
                      <span className={`${styles.badge} ${course.course_type === 'Core' ? styles.badgeCore : styles.badgeElective}`}>
                        {course.course_type}
                      </span>
                    </div>
                  </div>
                </div>

                <div className={styles.statusBadge}>
                  {course.completed ? (
                    <span className={`${styles.pill} ${styles.pillDone}`}>
                      <CheckCircle2 size={12}/> Completed
                    </span>
                  ) : course.prerequisites.length === 0 ? (
                    <span className={`${styles.pill} ${styles.pillOpen}`}>
                      <CheckCircle2 size={12}/> Open
                    </span>
                  ) : course.eligible ? (
                    <span className={`${styles.pill} ${styles.pillEligible}`}>
                      <CheckCircle2 size={12}/> Eligible
                    </span>
                  ) : (
                    <span className={`${styles.pill} ${styles.pillBlocked}`}>
                      <XCircle size={12}/> {course.missing_prerequisites.length} prereq{course.missing_prerequisites.length > 1 ? 's' : ''} missing
                    </span>
                  )}
                </div>
              </div>

              {/* Prerequisites section */}
              <div className={styles.prereqSection}>
                <span className={styles.prereqHeading}>
                  {course.prerequisites.length === 0 ? 'Prerequisites' : `Prerequisites (${course.prerequisites.length})`}
                </span>
                {course.prerequisites.length === 0 ? (
                  <span className={styles.noPrereq}>None — open to all eligible students</span>
                ) : (
                  <div className={styles.prereqChips}>
                    {course.prerequisites.map(p => {
                      const met = !course.missing_prerequisites.some(m => m.required_course_code === p.required_course_code)
                      return (
                        <span
                          key={p.required_course_code}
                          className={`${styles.chip} ${met ? styles.chipMet : styles.chipMissing}`}
                          title={p.course_name}
                        >
                          {met
                            ? <CheckCircle2 size={11}/>
                            : <XCircle size={11}/>
                          }
                          <span className={styles.chipCode}>{p.required_course_code}</span>
                          <span className={styles.chipName}>{p.course_name}</span>
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
