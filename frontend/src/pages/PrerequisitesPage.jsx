import { useEffect, useState } from 'react'
import { studentApi } from '../services/api'
import { Badge, PageSpinner, PageHeader, Alert, Card, EmptyState } from '../components/ui'
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import styles from './PrerequisitesPage.module.css'

export default function PrerequisitesPage() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    studentApi.prerequisites()
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load prerequisites.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageSpinner />
  if (error) return <Alert type="danger">{error}</Alert>

  const eligible = data.filter(c => c.eligible && !c.completed)
  const blocked = data.filter(c => !c.eligible && !c.completed)
  const done = data.filter(c => c.completed)

  const displayed = filter === 'eligible' ? eligible
    : filter === 'blocked' ? blocked
    : filter === 'done' ? done
    : data

  return (
    <div className="fade-in">
      <PageHeader title="Prerequisites Check" subtitle="See which courses you're eligible to take based on your completed courses" />

      <div className={styles.summaryRow}>
        <button className={`${styles.summaryCard} ${filter === 'all' ? styles.active : ''}`} onClick={() => setFilter('all')}>
          <AlertCircle size={18} color="var(--text-secondary)" />
          <span className={styles.sumNum}>{data.length}</span>
          <span className={styles.sumLabel}>Total tracked</span>
        </button>
        <button className={`${styles.summaryCard} ${styles.successCard} ${filter === 'eligible' ? styles.active : ''}`} onClick={() => setFilter('eligible')}>
          <CheckCircle2 size={18} color="var(--success)" />
          <span className={`${styles.sumNum} ${styles.green}`}>{eligible.length}</span>
          <span className={styles.sumLabel}>Eligible now</span>
        </button>
        <button className={`${styles.summaryCard} ${styles.dangerCard} ${filter === 'blocked' ? styles.active : ''}`} onClick={() => setFilter('blocked')}>
          <XCircle size={18} color="var(--danger)" />
          <span className={`${styles.sumNum} ${styles.red}`}>{blocked.length}</span>
          <span className={styles.sumLabel}>Prereqs missing</span>
        </button>
        <button className={`${styles.summaryCard} ${filter === 'done' ? styles.active : ''}`} onClick={() => setFilter('done')}>
          <CheckCircle2 size={18} color="var(--accent-text)" />
          <span className={`${styles.sumNum} ${styles.blue}`}>{done.length}</span>
          <span className={styles.sumLabel}>Completed</span>
        </button>
      </div>

      {displayed.length === 0 && <EmptyState icon="✅" title="Nothing to show" desc="No courses match this filter." />}

      <div className={styles.list}>
        {displayed.map(item => (
          <Card key={item.course_code} className={styles.itemCard}>
            <div className={styles.itemTop}>
              <div className={styles.itemLeft}>
                <span className={styles.code}>{item.course_code}</span>
                <div>
                  <p className={styles.name}>{item.course_name}</p>
                  <div className={styles.prereqList}>
                    <span className={styles.prereqLabel}>Requires: </span>
                    {item.prerequisites.map(p => (
                      <span key={p.required_course_code} className={`${styles.prereqChip} ${item.missing_prerequisites.some(m => m.required_course_code === p.required_course_code) ? styles.prereqMissing : styles.prereqMet}`}>
                        {p.required_course_code}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className={styles.itemStatus}>
                {item.completed ? (
                  <Badge variant="success">✓ Completed</Badge>
                ) : item.eligible ? (
                  <div className={styles.eligibleBadge}>
                    <CheckCircle2 size={14} color="var(--success)" />
                    <span>Eligible</span>
                  </div>
                ) : (
                  <div className={styles.blockedBadge}>
                    <XCircle size={14} color="var(--danger)" />
                    <span>Missing {item.missing_prerequisites.length} prereq{item.missing_prerequisites.length > 1 ? 's' : ''}</span>
                  </div>
                )}
              </div>
            </div>

            {item.missing_prerequisites.length > 0 && (
              <div className={styles.missingBlock}>
                <p className={styles.missingLabel}>Complete these first:</p>
                {item.missing_prerequisites.map(m => (
                  <span key={m.required_course_code} className={styles.missingCourse}>
                    {m.required_course_code} — {m.course_name}
                  </span>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}
