import { motion } from 'framer-motion'
import './StatusIndicator.css'

interface StatusIndicatorProps {
  status: 'listening' | 'thinking' | 'speaking' | 'connecting' | 'initializing' | 'disconnected'
}

function StatusIndicator({ status }: StatusIndicatorProps) {
  return (
    <div className="status-indicator">
      <motion.div 
        className={`status-dot ${status}`}
        animate={{ 
          scale: status === 'speaking' ? [1, 1.2, 1] : 1,
        }}
        transition={{ 
          repeat: status === 'speaking' ? Infinity : 0, 
          duration: 0.8 
        }}
      />
      <span className="status-text">
        {status === 'listening' && 'Listening...'}
        {status === 'thinking' && 'Thinking...'}
        {status === 'speaking' && 'Speaking...'}
        {status === 'connecting' && 'Connecting...'}
        {status === 'initializing' && 'Initializing...'}
        {status === 'disconnected' && 'Disconnected'}
      </span>
    </div>
  )
}

export default StatusIndicator

