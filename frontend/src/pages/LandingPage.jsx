import { Link } from 'react-router-dom'
import styles from './LandingPage.module.css'

export default function LandingPage() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <div className={styles.navLogo}>
          <img src="/logo.jpeg" alt="CourseWeave" className={styles.logoImg} />
        </div>
        <div className={styles.navLinks}>
          <Link to="/login" className={styles.loginLink}>Log in</Link>
          <Link to="/signup" className={styles.signupBtn}>Get started</Link>
        </div>
      </nav>

      <section className={styles.hero}>
        <div className={styles.heroTag}>Northeastern University · Graduate Programs</div>
        <h1 className={styles.heroTitle}>
          Your academic path,<br />
          <span className={styles.highlight}>intelligently planned.</span>
        </h1>
        <p className={styles.heroSub}>
          CourseWeave AI recommends the right courses for your career goals — checking prerequisites, 
          tracking your progress, and building a semester-by-semester roadmap. Powered by RAG and real job market data.
        </p>
        <div className={styles.heroActions}>
          <Link to="/signup" className={styles.primaryBtn}>Start planning for free</Link>
          <Link to="/login" className={styles.secondaryBtn}>Sign in</Link>
        </div>

        <div className={styles.statsRow}>
          {[
            { n: '500+', l: 'NEU courses indexed' },
            { n: '5', l: 'Graduate programs' },
            { n: 'RAG', l: 'Powered recommendations' },
            { n: '24/7', l: 'AI advisor access' },
          ].map(s => (
            <div key={s.l} className={styles.statItem}>
              <span className={styles.statNum}>{s.n}</span>
              <span className={styles.statLab}>{s.l}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.features}>
        {[
          { icon: '🎯', title: 'Career-aligned courses', desc: 'Tell us your goal — Data Engineer, Data Scientist, or ML Engineer — and get courses that match real job requirements from Adzuna job data.' },
          { icon: '🔗', title: 'Prerequisite validation', desc: 'Never get stuck. CourseWeave automatically checks your completed courses against prerequisites before recommending anything.' },
          { icon: '🗺️', title: 'Semester roadmap', desc: 'See your full degree journey semester by semester, with completed courses, current semester, and future planning all in one view.' },
          { icon: '📊', title: 'Progress tracking', desc: 'Track credits, GPA, core vs elective balance, and degree completion percentage — all updated in real time.' },
          { icon: '🤖', title: 'AI-powered advisor', desc: 'Ask questions in plain English. The RAG pipeline searches course descriptions, syllabi, and program requirements to answer precisely.' },
          { icon: '✅', title: 'Degree audit', desc: 'Know exactly what you need to graduate. Core requirements, elective choices, and thesis/project paths — all computed automatically.' },
        ].map(f => (
          <div key={f.title} className={styles.featureCard}>
            <div className={styles.featureIcon}>{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </div>
        ))}
      </section>

      <footer className={styles.footer}>
        <p>© 2025 CourseWeave AI · IE 7374 Machine Learning Operations · Group 9</p>
      </footer>
    </div>
  )
}
