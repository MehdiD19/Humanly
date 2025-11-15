import { motion } from 'framer-motion'
import { Mic, MessageSquare, Zap, ShieldAlert } from 'lucide-react'
import './LandingPage.css'

interface LandingPageProps {
  onStart: () => void
  isLoading: boolean
}

function LandingPage({ onStart, isLoading }: LandingPageProps) {
  return (
    <div className="landing-container">
      <motion.div
        className="landing-content"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <motion.div
          className="landing-header"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <h1>Voice Chat with AI Agent</h1>
          <p>Connect and have a natural conversation with your AI companion</p>
        </motion.div>

        <motion.div
          className="features-grid"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="feature-card">
            <Mic className="feature-icon" size={32} />
            <h3>Real-time Voice</h3>
            <p>Natural speech-to-speech conversation with AI</p>
          </div>

          <div className="feature-card">
            <MessageSquare className="feature-icon" size={32} />
            <h3>Text Chat</h3>
            <p>Complementary text messaging for clarity</p>
          </div>

          <div className="feature-card">
            <Zap className="feature-icon" size={32} />
            <h3>Ultra-responsive</h3>
            <p>Powered by LiveKit for real-time communication</p>
          </div>
        </motion.div>

        <motion.button
          className="start-button"
          onClick={onStart}
          disabled={isLoading}
          whileHover={{ scale: isLoading ? 1 : 1.05 }}
          whileTap={{ scale: isLoading ? 1 : 0.95 }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          {isLoading ? (
            <>
              <span className="spinner"></span>
              Connecting...
            </>
          ) : (
            <>
              <Mic size={20} />
              Start Conversation
            </>
          )}
        </motion.button>

        <motion.button
          className="dashboard-button"
          onClick={() => {
            window.location.href = `${window.location.pathname}?mode=dashboard`
          }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.35 }}
        >
          <ShieldAlert size={20} />
          Escalation Dashboard
        </motion.button>

        <motion.p
          className="landing-footer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          No setup required. Click to connect and start talking.
        </motion.p>
      </motion.div>
    </div>
  )
}

export default LandingPage


