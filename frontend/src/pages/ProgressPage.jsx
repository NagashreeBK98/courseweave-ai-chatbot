import { useEffect, useState } from 'react'
import { studentApi } from '../services/api'
import { Badge, PageSpinner, PageHeader, Alert, Card, StatCard, EmptyState } from '../components/ui'
import styles from './ProgressPage.module.css'

const gradePoints = { 'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7, 'C+': 2.3, 'C': 2.0 }

function gradeVariant(g) {
  if (!g) return 'default'
  if (g === 'A' || g === 'A-') return 'success'
  if (g === 'B+' || g === 'B') return 'core'
  return 'warning'
}

export default function ProgressPage() {
  const [courses, setCourses] = useState([])
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([studentApi.courses(), studentApi.dashboard()])
      .then(([cr, dr]) => { setCourses(cr.data); setDashboard(dr.data) })
      .catch(() => setError('Failed to load progress data.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageSpinner />
  if (error) return <Alert type="danger">{error}</Alert>

  const stats = dashboard?.stats || {}
  const totalCredits = courses.reduce((s, c) => s + (c.credits || 0), 0)
  const coreCount = courses.filter(c => c.course_type === 'Core').length
  const electiveCount = courses.filter(c => c.course_type === 'Elective').length

  const gradeDistribution = {}
  courses.forEach(c => {
    if (c.grade) gradeDistribution[c.grade] = (gradeDistribution[c.grade] || 0) + 1
  })
  const maxGrade = Math.max(...Object.values(gradeDistribution), 1)

  const semesterGroups = {}
  courses.forEach(c => {
    const key = c.completed_at ? String(c.completed_at).slice(0, 7) : 'Unknown'
    if (!semesterGroups[key]) semesterGroups[key] = []
    semesterGroups[key].push(c)
  })

  return (
    <div className="fade-in">
      <PageHeader title="Progress Tracker" subtitle="Your complete academic performance overview" />

      <div className={styles.statsGrid}>
        <StatCard label="Total credits earned" value={totalCredits} sub={`of ${stats.total_required || 40} required`} accent="teal" />
        <StatCard label="Cumulative GPA" value={(stats.gpa || 0).toFixed(2)} sub={stats.gpa >= 3.5 ? 'Excellent standing' : stats.gpa >= 3.0 ? 'Good standing' : 'Satisfactory'} accent={stats.gpa >= 3.5 ? 'teal' : 'blue'} />
        <StatCard label="Core courses" value={coreCount} sub="Completed" accent="blue" />
        <StatCard label="Electives" value={electiveCount} sub="Completed" accent="blue" />
      </div>

      <div className={styles.twoCol}>
        {/* Grade distribution */}
        <Card>
          <h3 className={styles.cardTitle}>Grade distribution</h3>
          {Object.keys(gradePoints).map(grade => {
            const count = gradeDistribution[grade] || 0
            const width = count === 0 ? 0 : Math.max((count / maxGrade) * 100, 4)
            return (
              <div key={grade} className={styles.gradeRow}>
                <span className={styles.gradeLabel}>{grade}</span>
                <div className={styles.gradeTrack}>
                  <div
                    className={styles.gradeFill}
                    style={{
                      width: `${width}%`,
                      background: grade.startsWith('A') ? 'var(--success)' : grade.startsWith('B') ? 'var(--accent)' : 'var(--warning)'
                    }}
                  />
                </div>
                <span className={styles.gradeCount}>{count}</span>
              </div>
            )
          })}
          {courses.length === 0 && <p style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>No grades recorded yet.</p>}
        </Card>

        {/* Credit breakdown */}
        <Card>
          <h3 className={styles.cardTitle}>Credit breakdown</h3>
          <div className={styles.creditBars}>
            {[
              { label: 'Core credits', val: coreCount * 4, total: stats.total_required || 40, color: 'var(--accent)' },
              { label: 'Elective credits', val: electiveCount * 4, total: stats.total_required || 40, color: 'var(--success)' },
              { label: 'Total completed', val: totalCredits, total: stats.total_required || 40, color: 'var(--text-primary)' },
            ].map(b => (
              <div key={b.label} className={styles.creditRow}>
                <div className={styles.creditMeta}>
                  <span className={styles.creditLabel}>{b.label}</span>
                  <span className={styles.creditVal}>{b.val} / {b.total}</span>
                </div>
                <div className={styles.creditTrack}>
                  <div className={styles.creditFill} style={{ width: `${Math.min((b.val / b.total) * 100, 100)}%`, background: b.color }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Full course history */}
      <div className={styles.historySection}>
        <h3 className={styles.cardTitle} style={{ marginBottom: 16 }}>Course history</h3>
        {Object.keys(semesterGroups).length === 0 && <EmptyState icon="📚" title="No courses yet" desc="Courses you've completed will appear here." />}
        {Object.entries(semesterGroups).sort(([a], [b]) => a.localeCompare(b)).map(([sem, list]) => (
          <div key={sem} className={styles.semGroup}>
            <div className={styles.semLabel}>{sem}</div>
            <div className={styles.semCourses}>
              {list.map(c => (
                <Card key={c.course_code} className={styles.historyCard}>
                  <div className={styles.historyLeft}>
                    <span className={styles.histCode}>{c.course_code}</span>
                    <div>
                      <p className={styles.histName}>{c.course_name}</p>
                      <p className={styles.histMeta}>{c.credits} credits</p>
                    </div>
                  </div>
                  <div className={styles.histRight}>
                    <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
                    {c.grade && <Badge variant={gradeVariant(c.grade)}>{c.grade}</Badge>}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
