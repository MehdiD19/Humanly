import { useState } from 'react'
import AgentVoiceChat from './components/AgentVoiceChat'
import LandingPage from './components/LandingPage'

function App() {
  // For demo purposes, use a simple user ID
  // In production, this would come from authentication
  const [userId] = useState(() => {
    // Generate or retrieve user ID (could be from localStorage, auth, etc.)
    const stored = localStorage.getItem('userId')
    if (stored) return stored
    const newId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('userId', newId)
    return newId
  })

  const [hasStarted, setHasStarted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleStart = () => {
    setIsLoading(true)
    // Small delay to show loading state
    setTimeout(() => {
      setHasStarted(true)
      setIsLoading(false)
    }, 500)
  }

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {!hasStarted ? (
        <LandingPage onStart={handleStart} isLoading={isLoading} />
      ) : (
        <AgentVoiceChat userId={userId} userName="User" />
      )}
    </div>
  )
}

export default App

