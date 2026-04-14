import { useState, useRef, useEffect } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { recommendApi } from '../services/api'
import { Bot, X, Send, Minimize2, ExternalLink } from 'lucide-react'
import styles from './FloatingChat.module.css'

export default function FloatingChat() {
  const { student } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [convId, setConvId] = useState(null)
  const bottomRef = useRef(null)

  const greeting = `Hi ${student?.name?.split(' ')[0] || 'there'}! Ask me anything about your courses or degree plan.`
  const [messages, setMessages] = useState([{ role: 'bot', text: greeting }])

  // Hide on the full advisor page — it's redundant there
  if (location.pathname === '/advisor') return null

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  const send = async (text) => {
    const userText = text || input.trim()
    if (!userText || loading) return
    setInput('')

    setMessages(prev => [...prev, { role: 'user', text: userText }])
    const loadingId = Date.now()
    setMessages(prev => [...prev, { role: 'bot', text: '', loading: true, id: loadingId }])
    setLoading(true)

    try {
      const r = await recommendApi.get({
        career_goal:     student?.target_career,
        conversation_id: convId,
        user_message:    userText,
      })
      const data = r.data
      const reply = data.recommendation || 'I couldn\'t get a response right now. Try the full AI Advisor.'
      const courses = data.action === 'recommend' ? (data.courses || []) : []

      setMessages(prev => prev.map(m =>
        m.id === loadingId ? { role: 'bot', text: reply, courses } : m
      ))
      if (data.conversation_id) setConvId(data.conversation_id)
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === loadingId ? { role: 'bot', text: 'Connection error. Please try again.' } : m
      ))
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button className={styles.fab} onClick={() => setOpen(true)} title="Ask AI Advisor">
          <Bot size={22} />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className={styles.panel}>
          <div className={styles.header}>
            <div className={styles.headerLeft}>
              <div className={styles.headerIcon}><Bot size={15} /></div>
              <div>
                <p className={styles.headerTitle}>AI Advisor</p>
                <p className={styles.headerSub}>CourseWeave · Gemini 2.5</p>
              </div>
            </div>
            <div className={styles.headerActions}>
              <Link to="/advisor" className={styles.expandBtn} title="Open full advisor">
                <ExternalLink size={13} />
              </Link>
              <button className={styles.closeBtn} onClick={() => setOpen(false)} title="Minimize">
                <Minimize2 size={13} />
              </button>
            </div>
          </div>

          <div className={styles.messages}>
            {messages.map((msg, i) => (
              <div key={i} className={`${styles.msg} ${msg.role === 'user' ? styles.userMsg : styles.botMsg}`}>
                {msg.loading ? (
                  <div className={styles.dots}><span /><span /><span /></div>
                ) : (
                  <>
                    <p className={styles.msgText}>{msg.text}</p>
                    {msg.courses?.length > 0 && (
                      <div className={styles.courseList}>
                        {msg.courses.slice(0, 3).map((c, j) => (
                          <div key={j} className={styles.courseChip}>
                            <span className={styles.courseCode}>{c.course_code}</span>
                            <span className={styles.courseName}>{c.course_name}</span>
                          </div>
                        ))}
                        {msg.courses.length > 3 && (
                          <p className={styles.moreHint}>+{msg.courses.length - 3} more — <Link to="/advisor" className={styles.moreLink}>see full response</Link></p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {messages.length === 1 && (
            <div className={styles.suggestions}>
              {['What should I take next?', 'Am I on track to graduate?', 'Best electives for my career?'].map(s => (
                <button key={s} className={styles.sugBtn} onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          )}

          <div className={styles.inputRow}>
            <textarea
              className={styles.input}
              rows={1}
              placeholder="Ask anything…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
            />
            <button
              className={styles.sendBtn}
              onClick={() => send()}
              disabled={loading || !input.trim()}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
