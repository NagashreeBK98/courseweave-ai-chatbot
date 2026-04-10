import { useEffect, useState, useMemo } from 'react'
import { coursesApi, studentApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { Badge, PageSpinner, PageHeader, Alert, Card } from '../components/ui'
import { Search, Filter } from 'lucide-react'
import styles from './CatalogPage.module.css'

const PROGRAMS = ['All', 'MS_DAE', 'MS_DS', 'MS_CS', 'MS_DA', 'MS_IS']
const TYPES = ['All', 'Core', 'Elective']

export default function CatalogPage() {
  const { student } = useAuth()
  const [courses, setCourses] = useState([])
  const [completed, setCompleted] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [program, setProgram] = useState(student?.program_code || 'All')
  const [type, setType] = useState('All')

  useEffect(() => {
    Promise.all([coursesApi.list(), studentApi.courses()])
      .then(([cr, sr]) => {
        setCourses(cr.data)
        setCompleted(new Set(sr.data.map(c => c.course_code)))
      })
      .catch(() => setError('Failed to load courses.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    return courses.filter(c => {
      const matchSearch = !search || c.course_code.toLowerCase().includes(search.toLowerCase()) || c.course_name.toLowerCase().includes(search.toLowerCase())
      const matchProgram = program === 'All' || c.program_code === program
      const matchType = type === 'All' || c.course_type === type
      return matchSearch && matchProgram && matchType
    })
  }, [courses, search, program, type])

  if (loading) return <PageSpinner />

  return (
    <div className="fade-in">
      <PageHeader title="Course Catalog" subtitle={`${filtered.length} of ${courses.length} courses shown`} />
      {error && <Alert type="danger">{error}</Alert>}

      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <Search size={15} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search by course code or name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className={styles.filterGroup}>
          <Filter size={14} style={{ color: 'var(--text-tertiary)' }} />
          <select className={styles.select} value={program} onChange={e => setProgram(e.target.value)}>
            {PROGRAMS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <select className={styles.select} value={type} onChange={e => setType(e.target.value)}>
            {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      <div className={styles.grid}>
        {filtered.map(c => (
          <Card key={c.course_code} className={`${styles.courseCard} ${completed.has(c.course_code) ? styles.done : ''}`}>
            <div className={styles.cardTop}>
              <span className={styles.code}>{c.course_code}</span>
              <div className={styles.badges}>
                <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
                {completed.has(c.course_code) && <Badge variant="success">✓ Done</Badge>}
              </div>
            </div>
            <h3 className={styles.name}>{c.course_name}</h3>
            <div className={styles.cardMeta}>
              <span className={styles.program}>{c.program_code}</span>
              <span className={styles.credits}>{c.credits} credits</span>
            </div>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className={styles.noResults}>
            <p>No courses match your filters.</p>
            <button onClick={() => { setSearch(''); setProgram('All'); setType('All') }} className={styles.clearBtn}>Clear filters</button>
          </div>
        )}
      </div>
    </div>
  )
}
