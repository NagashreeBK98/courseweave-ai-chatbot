import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from './AuthPage.module.css'

const PROGRAMS = [
  { code: 'MS_DAE', label: 'MS Data Analytics Engineering' },
  { code: 'MS_DS',  label: 'MS Data Science' },
  { code: 'MS_CS',  label: 'MS Computer Science' },
  { code: 'MS_DA',  label: 'MS Data Analytics' },
  { code: 'MS_IS',  label: 'MS Information Systems' },
]

const CAREERS = [
  'Data Engineer', 'Data Scientist', 'Data Analyst',
  'Business Analyst', 'Software Engineer', 'ML Engineer',
]

const TRACKS = [
  { value: 'coursework', label: 'Coursework — all electives' },
  { value: 'project',    label: 'Project — IE 7945 + fewer electives' },
  { value: 'thesis',     label: 'Thesis — research + fewer electives' },
]

export default function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name:'', email:'', password:'', program_code:'', target_career:'', degree_path:'' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handle = (e) => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await signup(form)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed. Please try again.')
    } finally { setLoading(false) }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card} style={{ maxWidth: 480 }}>
        <Link to="/" className={styles.backLogo}>
          <img src="/logo_bg.png" alt="CourseWeave" className={styles.logoImg} />
        </Link>

        <h1 className={styles.title}>Create your account</h1>
        <p className={styles.sub}>Start planning your academic journey</p>

        {error && <div className={styles.error}>{error}</div>}

        <form onSubmit={submit} className={styles.form}>
          <div className={styles.field}>
            <label>Full name</label>
            <input name="name" placeholder="Aisha Patel" value={form.name} onChange={handle} required />
          </div>
          <div className={styles.field}>
            <label>NEU Email</label>
            <input type="email" name="email" placeholder="you@northeastern.edu" value={form.email} onChange={handle} required />
          </div>
          <div className={styles.field}>
            <label>Password</label>
            <input type="password" name="password" placeholder="Min 8 characters" value={form.password} onChange={handle} required minLength={8} />
          </div>
          <div className={styles.field}>
            <label>Graduate program</label>
            <select name="program_code" value={form.program_code} onChange={handle} required>
              <option value="">Select your program…</option>
              {PROGRAMS.map(p => <option key={p.code} value={p.code}>{p.label}</option>)}
            </select>
          </div>
          <div className={styles.field}>
            <label>Career goal</label>
            <select name="target_career" value={form.target_career} onChange={handle} required>
              <option value="">Select your target role…</option>
              {CAREERS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className={styles.field}>
            <label>Degree track</label>
            <select name="degree_path" value={form.degree_path} onChange={handle}>
              <option value="">Undecided — I'll choose later</option>
              {TRACKS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className={styles.switchLink}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
