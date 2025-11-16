import { motion } from 'framer-motion'
import { Mic, ShieldAlert } from 'lucide-react'
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
          <h1>Humanly</h1>
          <p>Your Digital Twin. AI that knows when decisions need you.</p>
        </motion.div>

        <motion.div
          className="buttons-container"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
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
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <ShieldAlert size={20} />
            Escalation Dashboard
          </motion.button>
        </motion.div>

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


