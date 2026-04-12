import { useEffect, useState } from 'react'
import { X, BookOpen, GraduationCap, Clock, FileText } from 'lucide-react'
import { coursesApi } from '../services/api'
import styles from './CourseDetailsModal.module.css'

export default function CourseDetailsModal({ courseCode, onClose }) {
  const [loading, setLoading] = useState(true)
  const [details, setDetails] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!courseCode) return

    setLoading(true)
    setError('')

    coursesApi.getDetails(courseCode)
      .then(r => setDetails(r.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load course details'))
      .finally(() => setLoading(false))
  }, [courseCode])

  return (
    <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>

        <div className={styles.header}>
          <div>
            <div className={styles.codeChip}>{courseCode}</div>
            <h2 className={styles.title}>{loading ? 'Loading...' : details?.course_name}</h2>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className={styles.body}>
          {loading && (
            <div className={styles.loader}>
              <div className={styles.spinner}></div>
              <p>Loading course details...</p>
            </div>
          )}

          {error && (
            <div className={styles.error}>
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && details && (
            <>
              {/* Course metadata */}
              <div className={styles.metaRow}>
                <div className={styles.metaItem}>
                  <Clock size={16} />
                  <span>{details.credits} Credits</span>
                </div>
                <div className={styles.metaItem}>
                  <GraduationCap size={16} />
                  <span>{details.course_type}</span>
                </div>
              </div>

              {/* AI Summary */}
              {details.ai_summary && (
                <div className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <BookOpen size={18} />
                    <h3>Course Overview</h3>
                  </div>
                  <div className={styles.aiContent}>
                    {details.ai_summary.split('\n').map((line, i) => (
                      line.trim() ? <p key={i}>{line}</p> : <br key={i} />
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {details.description && (
                <div className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <FileText size={18} />
                    <h3>Description</h3>
                  </div>
                  <p className={styles.description}>{details.description}</p>
                </div>
              )}

              {/* Learning Outcomes */}
              {details.learning_outcomes && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Learning Outcomes</h3>
                  <p className={styles.outcomes}>{details.learning_outcomes}</p>
                </div>
              )}

              {/* Prerequisites */}
              {details.prerequisites && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Prerequisites</h3>
                  <p className={styles.prereqs}>{details.prerequisites}</p>
                </div>
              )}

              {/* Syllabus excerpt */}
              {details.syllabus_text && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Syllabus Excerpt</h3>
                  <div className={styles.syllabusBox}>
                    <p className={styles.syllabusText}>{details.syllabus_text}</p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

      </div>
    </div>
  )
}
