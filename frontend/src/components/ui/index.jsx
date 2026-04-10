import styles from './UI.module.css'

export function Badge({ children, variant = 'default' }) {
  return <span className={`${styles.badge} ${styles[variant]}`}>{children}</span>
}

export function Card({ children, className = '', style }) {
  return <div className={`${styles.card} ${className}`} style={style}>{children}</div>
}

export function Spinner({ size = 20 }) {
  return (
    <div className={styles.spinnerWrap}>
      <div className={styles.spinner} style={{ width: size, height: size }} />
    </div>
  )
}

export function PageSpinner() {
  return (
    <div className={styles.pageSpinner}>
      <div className={styles.spinner} style={{ width: 28, height: 28 }} />
      <span>Loading…</span>
    </div>
  )
}

export function StatCard({ label, value, sub, accent }) {
  return (
    <div className={`${styles.statCard} ${accent ? styles.accentStat : ''}`}>
      <p className={styles.statLabel}>{label}</p>
      <p className={`${styles.statValue} ${accent ? styles[accent] : ''}`}>{value}</p>
      {sub && <p className={styles.statSub}>{sub}</p>}
    </div>
  )
}

export function EmptyState({ icon, title, desc }) {
  return (
    <div className={styles.empty}>
      <div className={styles.emptyIcon}>{icon}</div>
      <p className={styles.emptyTitle}>{title}</p>
      {desc && <p className={styles.emptyDesc}>{desc}</p>}
    </div>
  )
}

export function SectionHeader({ title, action }) {
  return (
    <div className={styles.sectionHeader}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {action}
    </div>
  )
}

export function PageHeader({ title, subtitle }) {
  return (
    <div className={styles.pageHeader}>
      <h1 className={styles.pageTitle}>{title}</h1>
      {subtitle && <p className={styles.pageSubtitle}>{subtitle}</p>}
    </div>
  )
}

export function Alert({ type = 'info', children }) {
  return <div className={`${styles.alert} ${styles[`alert_${type}`]}`}>{children}</div>
}
