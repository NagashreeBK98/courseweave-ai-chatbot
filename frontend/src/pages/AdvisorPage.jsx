import { useState, useRef, useEffect } from 'react'
import { recommendApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { Card, Badge } from '../components/ui'
import { Send, Bot, User, Sparkles, RefreshCw } from 'lucide-react'
import styles from './AdvisorPage.module.css'

const SUGGESTIONS = [
  'What courses should I take next semester?',
  'Which electives align with my career goal?',
  'Am I on track to graduate on time?',
  'What prerequisites do I still need?',
]

function Message({ msg }) {
  const isBot = msg.role === 'bot'
  return (
    <div className={`${styles.msgWrap} ${isBot ? styles.botWrap : styles.userWrap}`}>
      <div className={styles.msgAvatar}>
        {isBot ? <Bot size={14} /> : <User size={14} />}
      </div>
      <div className={`${styles.bubble} ${isBot ? styles.botBubble : styles.userBubble}`}>
        {msg.loading ? (
          <div className={styles.typingDots}>
            <span /><span /><span />
          </div>
        ) : (
          <>
            <p className={styles.bubbleText}>{msg.text}</p>
            {msg.courses && msg.courses.length > 0 && (
              <div className={styles.courseCards}>
                {msg.courses.map((c, i) => (
                  <div key={i} className={styles.courseCard}>
                    <div className={styles.courseCardTop}>
                      <span className={styles.courseCode}>{c.course_code}</span>
                      <Badge variant={c.course_type === 'Core' ? 'core' : 'elective'}>{c.course_type}</Badge>
                    </div>
                    <p className={styles.courseCardName}>{c.course_name}</p>
                    {c.reason && <p className={styles.courseCardReason}>{c.reason}</p>}
                    <p className={styles.courseCardMeta}>{c.credits} credits</p>
                  </div>
                ))}
              </div>
            )}
            {msg.source === 'fallback' && (
              <p className={styles.fallbackNote}>⚠ RAG pipeline unavailable — showing catalog-based recommendations</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function AdvisorPage() {
  const { student } = useAuth()
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: `Hi ${student?.name?.split(' ')[0] || 'there'}! I'm your CourseWeave AI Advisor. I can recommend courses based on your career goal (${student?.target_career || 'your program'}), check prerequisites, and help you plan your semester. What would you like to know?`,
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const userText = text || input.trim()
    if (!userText || loading) return
    setInput('')

    setMessages(prev => [...prev, { role: 'user', text: userText }])

    const loadingId = Date.now()
    setMessages(prev => [...prev, { role: 'bot', text: '', loading: true, id: loadingId }])
    setLoading(true)

    try {
      const r = await recommendApi.get({ career_goal: student?.target_career })
      const data = r.data

      const recs = data.recommendations || []
      const replyText = recs.length > 0
        ? `Based on your goal of becoming a ${student?.target_career}, here are my top course recommendations for you:`
        : `I analyzed your academic profile, but couldn't find specific matches right now. Try browsing the course catalog or checking your prerequisites page.`

      setMessages(prev => prev.map(m =>
        m.id === loadingId
          ? { role: 'bot', text: replyText, courses: recs, source: data.source }
          : m
      ))
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === loadingId
          ? { role: 'bot', text: 'Sorry, I had trouble connecting to the recommendation service. Please check that the backend is running.' }
          : m
      ))
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const reset = () => {
    setMessages([{
      role: 'bot',
      text: `Hi again! What would you like to know about your ${student?.program_code} program?`,
    }])
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>
            <Sparkles size={18} style={{ color: 'var(--accent)' }} />
            AI Advisor
          </h1>
          <p className={styles.sub}>Powered by RAG · Gemini 2.5 Flash · Pinecone hybrid search</p>
        </div>
        <button className={styles.resetBtn} onClick={reset}>
          <RefreshCw size={14} /> New chat
        </button>
      </div>

      <div className={styles.chatArea}>
        <div className={styles.messages}>
          {messages.map((msg, i) => <Message key={i} msg={msg} />)}
          <div ref={bottomRef} />
        </div>

        {messages.length === 1 && (
          <div className={styles.suggestions}>
            <p className={styles.sugLabel}>Try asking:</p>
            <div className={styles.sugGrid}>
              {SUGGESTIONS.map(s => (
                <button key={s} className={styles.sugBtn} onClick={() => sendMessage(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className={styles.inputRow}>
          <textarea
            className={styles.input}
            rows={1}
            placeholder="Ask about courses, prerequisites, your career path…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading}
          />
          <button
            className={styles.sendBtn}
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
