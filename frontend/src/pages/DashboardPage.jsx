import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { studentApi } from '../services/api'
import { StatCard, Card, Badge, PageSpinner, SectionHeader, Alert } from '../components/ui'
import { ArrowRight, BookOpen, TrendingUp, Bot, UserCog } from 'lucide-react'
import AcademicProfileModal from './AcademicProfileModal'
import styles from './DashboardPage.module.css'

function gradeVariant(g) {
  if (!g) return 'default'
  if (g.startsWith('A')) return 'success'
  if (g.startsWith('B')) return 'core'
  return 'warning'
}

/* ── Completed courses table ── */
function CompletedTable({ rows }) {
  if (rows.length === 0) return (
    <p className={styles.emptyMsg}>No courses completed yet. Use "Setup Academic Profile" to add your completed courses.</p>
  )
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th style={{width: '12%'}}>Semester</th>
            <th style={{width: '10%'}}>Code</th>
            <th style={{width: '48%'}}>Course Name</th>
            <th className={styles.center} style={{width: '10%'}}>Credits</th>
            <th className={styles.center} style={{width: '12%'}}>Type</th>
            <th className={styles.center} style={{width: '8%'}}>Grade</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(c => (
            <tr key={c.course_code}>
              <td className={styles.semCell}>{c.semester || '—'}</td>
              <td><span className={styles.code}>{c.course_code}</span></td>
              <td className={styles.nameCell}>{c.course_name}</td>
              <td className={styles.center}><strong>{c.credits}</strong></td>
              <td className={styles.center}>
                <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
              </td>
              <td className={styles.center}>
                {c.grade ? <Badge variant={gradeVariant(c.grade)}>{c.grade}</Badge> : <span className={styles.dash}>—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Remaining courses table ── */
function RemainingTable({ rows }) {
  if (rows.length === 0) return (
    <p className={styles.emptyMsg}>🎉 All courses completed!</p>
  )
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Code</th>
            <th>Course Name</th>
            <th className={styles.center}>Credits</th>
            <th className={styles.center}>Type</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(c => (
            <tr key={c.course_code}>
              <td><span className={styles.code}>{c.course_code}</span></td>
              <td className={styles.nameCell}>{c.course_name}</td>
              <td className={styles.center}>{c.credits}</td>
              <td className={styles.center}>
                <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Recommended courses table ── */
function RecsTable({ rows }) {
  if (rows.length === 0) return (
    <p className={styles.emptyMsg}>🎉 All courses completed!</p>
  )
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th style={{width: '12%'}}>Code</th>
            <th style={{width: '66%'}}>Course Name</th>
            <th className={styles.center} style={{width: '10%'}}>Credits</th>
            <th className={styles.center} style={{width: '12%'}}>Type</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c, i) => (
            <tr key={c.course_code || i}>
              <td><span className={styles.code}>{c.course_code}</span></td>
              <td className={styles.nameCell}>{c.course_name}</td>
              <td className={styles.center}><strong>{c.credits || 4}</strong></td>
              <td className={styles.center}>
                <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type || 'Elective'}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DashboardPage() {
  const [data, setData]           = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [showModal, setShowModal] = useState(false)

  function loadDashboard() {
    return studentApi.dashboard().then(r => setData(r.data))
  }

  useEffect(() => {
    loadDashboard()
      .catch(() => setError('Failed to load dashboard. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  function handleProfileSubmit(semester) {
    setShowModal(false)
    loadDashboard()
  }

  if (loading) return <PageSpinner />
  if (error)   return <Alert type="danger">{error}</Alert>

  const { student, stats, completed_courses, remaining_courses } = data
  const pct = stats.progress_pct

  // Get recommended courses: prioritize Core, then Electives
  const coreCourses = remaining_courses.filter(c => c.course_type === 'Core').slice(0, 5)
  const electiveCourses = remaining_courses.filter(c => c.course_type === 'Elective').slice(0, 3)
  const recommendedCourses = [...coreCourses, ...electiveCourses].slice(0, 6)

  return (
    <div className="fade-in">

      {/* ── Welcome row ── */}
      <div className={styles.welcome}>
        <div>
          <h1 className={styles.welcomeTitle}>Good morning, {student.name.split(' ')[0]} 👋</h1>
          <p className={styles.welcomeSub}>Here's where you stand in your {student.program_code} program.</p>
        </div>
        <div className={styles.ctaGroup}>
          <button className={styles.profileCta} onClick={() => setShowModal(true)}>
            <UserCog size={14} />
            Setup Academic Profile
          </button>
          <Link to="/advisor" className={styles.advisorCta}>
            <Bot size={15} />
            Ask AI Advisor
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>

      {/* ── Stats grid ── */}
      <div className={styles.statsGrid}>
        <StatCard label="Credits completed"  value={`${stats.credits_completed} / ${stats.total_required}`} sub={`${pct}% of program done`} accent="teal" />
        <StatCard label="Courses completed"  value={stats.courses_completed} sub={`${stats.core_completed} core · ${stats.electives_completed} electives`} accent="blue" />
        <StatCard label="GPA"                value={stats.gpa.toFixed(2)} sub="Cumulative" accent={stats.gpa >= 3.5 ? 'teal' : stats.gpa >= 3.0 ? 'blue' : 'amber'} />
        <StatCard label="Credits remaining"  value={stats.credits_remaining} sub="To graduation" accent={stats.credits_remaining <= 8 ? 'teal' : 'amber'} />
      </div>

      {/* ── Progress bar ── */}
      <Card className={styles.progressCard}>
        <div className={styles.progressHeader}>
          <span className={styles.progressLabel}>Degree progress</span>
          <span className={styles.progressPct}>{pct}%</span>
        </div>
        <div className={styles.progressTrack}>
          <div className={styles.progressFill} style={{ width: `${pct}%` }} />
        </div>
        <div className={styles.progressMeta}>
          <span>{stats.credits_completed} credits earned</span>
          <span>{stats.credits_remaining} credits remaining to graduation</span>
        </div>
      </Card>

      {/* ── Completed Courses Table ── */}
      <div className={styles.section}>
        <SectionHeader
          title="Completed Courses"
          action={<Link to="/progress" className={styles.seeAll}>View all <ArrowRight size={12} /></Link>}
        />
        <CompletedTable rows={completed_courses} />
      </div>

      {/* ── Recommended Next Courses ── */}
      <div className={styles.section}>
        <SectionHeader
          title="Recommended Next Courses"
          action={<Link to="/advisor" className={styles.seeAll}>Get AI Picks <ArrowRight size={12} /></Link>}
        />
        <RecsTable rows={recommendedCourses} />
        <div className={styles.quickLinks}>
          <Link to="/roadmap" className={styles.quickLink}><TrendingUp size={14} /> View Roadmap</Link>
          <Link to="/catalog" className={styles.quickLink}><BookOpen size={14} /> Browse Catalog</Link>
          <Link to="/advisor" className={styles.quickLink}><Bot size={14} /> Ask AI Advisor</Link>
        </div>
      </div>

      {/* ── Modal ── */}
      {showModal && (
        <AcademicProfileModal
          onClose={() => setShowModal(false)}
          onSubmit={handleProfileSubmit}
        />
      )}

    </div>
  )
}
