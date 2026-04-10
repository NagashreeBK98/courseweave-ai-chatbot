import { useEffect, useState } from 'react'
import { studentApi } from '../services/api'
import { Badge, PageSpinner, PageHeader, Alert } from '../components/ui'
import { CheckCircle2, Circle, Clock } from 'lucide-react'
import styles from './RoadmapPage.module.css'

const statusIcon = { completed: CheckCircle2, current: Clock, planned: Circle }
const statusColor = { completed: 'var(--success)', current: 'var(--accent)', planned: 'var(--border-strong)' }

export default function RoadmapPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    studentApi.roadmap()
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load roadmap.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageSpinner />
  if (error) return <Alert type="danger">{error}</Alert>

  const { semesters } = data

  return (
    <div className="fade-in">
      <PageHeader title="My Roadmap" subtitle="Your semester-by-semester academic journey" />

      <div className={styles.timeline}>
        {semesters.map((sem, idx) => {
          const Icon = statusIcon[sem.status]
          const color = statusColor[sem.status]
          const totalCredits = sem.courses.reduce((s, c) => s + (c.credits || 0), 0)
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
                    {sem.courses.length} courses · {totalCredits} credits
                    {sem.status === 'completed' && <span className={styles.completedTag}>Completed</span>}
                    {sem.status === 'current' && <span className={styles.currentTag}>Current semester</span>}
                    {sem.status === 'planned' && <span className={styles.plannedTag}>Planned</span>}
                  </div>
                </div>
              </div>

              <div className={styles.courseGrid}>
                {sem.courses.map(c => (
                  <div key={c.course_code} className={`${styles.courseChip} ${styles[`chip_${sem.status}`]}`}>
                    <div className={styles.chipTop}>
                      <span className={styles.chipCode}>{c.course_code}</span>
                      <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
                      {c.grade && <Badge variant="success">{c.grade}</Badge>}
                    </div>
                    <p className={styles.chipName}>{c.course_name}</p>
                    <p className={styles.chipCredits}>{c.credits} credits</p>
                  </div>
                ))}
              </div>
            </div>
          )
        })}

        {semesters.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '48px 0' }}>
            No roadmap data yet. Complete your profile to get started.
          </div>
        )}
      </div>
    </div>
  )
}
