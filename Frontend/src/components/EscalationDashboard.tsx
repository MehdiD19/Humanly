import { useState, useEffect, useRef } from 'react'

interface Escalation {
  escalation_id: string
  room_name: string
  user_id: string
  reason: string
  urgency: 'low' | 'medium' | 'high' | 'critical'
  decision_type: string
  context_details: string
  recent_transcript: Array<{ role: string; content: string; timestamp: string }>
  status: 'pending' | 'resolved'
  created_at: string
  human_response?: string
  responded_at?: string
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function EscalationDashboard() {
  const [escalations, setEscalations] = useState<Escalation[]>([])
  const [selectedEscalation, setSelectedEscalation] = useState<Escalation | null>(null)
  const [responseText, setResponseText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)

  // Connect to WebSocket
  useEffect(() => {
    const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
    const ws = new WebSocket(`${wsUrl}/ws/frontend`)

    ws.onopen = () => {
      console.log('✅ Connected to WebSocket')
      setConnectionStatus('connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'initial_state') {
          setEscalations(data.escalations || [])
        } else if (data.type === 'new_escalation') {
          setEscalations(prev => {
            const exists = prev.find(e => e.escalation_id === data.escalation.escalation_id)
            if (exists) return prev
            return [data.escalation, ...prev]
          })
        } else if (data.type === 'escalation_resolved') {
          setEscalations(prev =>
            prev.map(e =>
              e.escalation_id === data.escalation_id ? data.escalation : e
            )
          )
          if (selectedEscalation?.escalation_id === data.escalation_id) {
            setSelectedEscalation(data.escalation)
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setConnectionStatus('disconnected')
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
      setConnectionStatus('disconnected')
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        setConnectionStatus('connecting')
      }, 3000)
    }

    wsRef.current = ws

    // Load initial escalations via HTTP
    fetchPendingEscalations()

    return () => {
      ws.close()
    }
  }, [])

  const fetchPendingEscalations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/escalations/pending`)
      const data = await response.json()
      setEscalations(data.escalations || [])
    } catch (error) {
      console.error('Error fetching escalations:', error)
    }
  }

  const handleSelectEscalation = async (escalation: Escalation) => {
    if (escalation.escalation_id === selectedEscalation?.escalation_id) {
      setSelectedEscalation(null)
      setResponseText('')
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/escalations/${escalation.escalation_id}`)
      const fullEscalation = await response.json()
      setSelectedEscalation(fullEscalation)
      setResponseText('')
    } catch (error) {
      console.error('Error fetching escalation details:', error)
    }
  }

  const handleSubmitResponse = async () => {
    if (!selectedEscalation || !responseText.trim()) return

    setIsSubmitting(true)
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/escalations/${selectedEscalation.escalation_id}/respond`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            response_text: responseText.trim(),
          }),
        }
      )

      if (response.ok) {
        setResponseText('')
        setSelectedEscalation(null)
        await fetchPendingEscalations()
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail || 'Failed to submit response'}`)
      }
    } catch (error) {
      console.error('Error submitting response:', error)
      alert('Failed to submit response. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'bg-red-600 text-white'
      case 'high':
        return 'bg-orange-500 text-white'
      case 'medium':
        return 'bg-yellow-500 text-black'
      case 'low':
        return 'bg-blue-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  const pendingEscalations = escalations.filter(e => e.status === 'pending')
  const resolvedEscalations = escalations.filter(e => e.status === 'resolved')

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">Escalation Dashboard</h1>
              <p className="text-gray-600 mt-1">Monitor and respond to agent escalations</p>
            </div>
            <div className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  connectionStatus === 'connected'
                    ? 'bg-green-500'
                    : connectionStatus === 'connecting'
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
              />
              <span className="text-sm text-gray-600">
                {connectionStatus === 'connected'
                  ? 'Connected'
                  : connectionStatus === 'connecting'
                  ? 'Connecting...'
                  : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Escalation List */}
          <div className="lg:col-span-2 space-y-4">
            {/* Pending Escalations */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Pending Escalations ({pendingEscalations.length})
              </h2>
              {pendingEscalations.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No pending escalations</p>
              ) : (
                <div className="space-y-3">
                  {pendingEscalations.map((escalation) => (
                    <div
                      key={escalation.escalation_id}
                      onClick={() => handleSelectEscalation(escalation)}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        selectedEscalation?.escalation_id === escalation.escalation_id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span
                              className={`px-2 py-1 rounded text-xs font-semibold ${getUrgencyColor(
                                escalation.urgency
                              )}`}
                            >
                              {escalation.urgency.toUpperCase()}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(escalation.created_at).toLocaleTimeString()}
                            </span>
                          </div>
                          <h3 className="font-semibold text-gray-800 mb-1">
                            {escalation.decision_type.replace('_', ' ').toUpperCase()}
                          </h3>
                          <p className="text-sm text-gray-600 line-clamp-2">
                            {escalation.reason}
                          </p>
                          <p className="text-xs text-gray-500 mt-2">
                            Room: {escalation.room_name} • User: {escalation.user_id}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Resolved Escalations */}
            {resolvedEscalations.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Resolved Escalations ({resolvedEscalations.length})
                </h2>
                <div className="space-y-3">
                  {resolvedEscalations.slice(0, 5).map((escalation) => (
                    <div
                      key={escalation.escalation_id}
                      className="p-4 rounded-lg border border-gray-200 bg-gray-50"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="px-2 py-1 rounded text-xs font-semibold bg-green-500 text-white">
                              RESOLVED
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(escalation.created_at).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 line-clamp-1">
                            {escalation.reason}
                          </p>
                          {escalation.human_response && (
                            <p className="text-xs text-gray-500 mt-2 italic">
                              Response: {escalation.human_response}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Response Panel */}
          <div className="lg:col-span-1">
            {selectedEscalation ? (
              <div className="bg-white rounded-lg shadow-md p-6 sticky top-4">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">Respond to Escalation</h2>

                {/* Escalation Details */}
                <div className="mb-6 space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-gray-700">Reason</label>
                    <p className="text-sm text-gray-600 mt-1">{selectedEscalation.reason}</p>
                  </div>

                  {selectedEscalation.context_details && (
                    <div>
                      <label className="text-sm font-semibold text-gray-700">Context Details</label>
                      <p className="text-sm text-gray-600 mt-1">
                        {selectedEscalation.context_details}
                      </p>
                    </div>
                  )}

                  {selectedEscalation.recent_transcript && selectedEscalation.recent_transcript.length > 0 && (
                    <div>
                      <label className="text-sm font-semibold text-gray-700 mb-2 block">
                        Recent Conversation
                      </label>
                      <div className="bg-gray-50 rounded p-3 max-h-48 overflow-y-auto">
                        {selectedEscalation.recent_transcript.map((msg, idx) => (
                          <div key={idx} className="mb-2 text-xs">
                            <span className="font-semibold text-gray-700">
                              {msg.role === 'user' ? 'User' : 'Agent'}:
                            </span>
                            <span className="text-gray-600 ml-2">{msg.content}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${getUrgencyColor(selectedEscalation.urgency)}`}>
                      {selectedEscalation.urgency.toUpperCase()}
                    </span>
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-gray-200 text-gray-700">
                      {selectedEscalation.decision_type.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Response Input */}
                {selectedEscalation.status === 'pending' ? (
                  <div>
                    <label className="text-sm font-semibold text-gray-700 mb-2 block">
                      Your Response
                    </label>
                    <textarea
                      value={responseText}
                      onChange={(e) => setResponseText(e.target.value)}
                      placeholder="Type your response here. This will be sent to the agent..."
                      className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={handleSubmitResponse}
                      disabled={!responseText.trim() || isSubmitting}
                      className="w-full mt-4 bg-blue-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {isSubmitting ? 'Submitting...' : 'Submit Response'}
                    </button>
                  </div>
                ) : (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <p className="text-sm font-semibold text-green-800 mb-2">Resolved</p>
                    {selectedEscalation.human_response && (
                      <p className="text-sm text-green-700">
                        Response: {selectedEscalation.human_response}
                      </p>
                    )}
                    {selectedEscalation.responded_at && (
                      <p className="text-xs text-green-600 mt-2">
                        Resolved at: {new Date(selectedEscalation.responded_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-md p-6 sticky top-4">
                <p className="text-gray-500 text-center py-8">
                  Select an escalation to view details and respond
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


