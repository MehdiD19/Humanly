import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  BarVisualizer,
  useLocalParticipant,
} from '@livekit/components-react'
import '@livekit/components-styles'
import { Mic, MicOff, Phone, Loader2, Settings, MessageSquare, Volume2, X } from 'lucide-react'
import { livekitService } from '../services/livekitService'
import AgentTextChat from './AgentTextChat'
import './AgentVoiceChat.css'

interface AgentVoiceChatProps {
  userId: string
  userName: string
}

function AgentVoiceChat({ userId }: AgentVoiceChatProps) {
  const [token, setToken] = useState<string>('')
  const [serverUrl, setServerUrl] = useState<string>('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string>('')
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([])
  const [audioOutputDevices, setAudioOutputDevices] = useState<MediaDeviceInfo[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string>('')
  const [devicesLoaded, setDevicesLoaded] = useState(false)
  const hasAttemptedConnect = useRef(false)

  // Load available audio devices
  useEffect(() => {
    const loadAudioDevices = async () => {
      try {
        // Request permission first
        await navigator.mediaDevices.getUserMedia({ audio: true })
        
        // Get all devices
        const devices = await navigator.mediaDevices.enumerateDevices()
        const audioInputs = devices.filter(device => device.kind === 'audioinput')
        const audioOutputs = devices.filter(device => device.kind === 'audiooutput')
        setAudioDevices(audioInputs)
        setAudioOutputDevices(audioOutputs)
        
        // Set default device if not already set
        if (!selectedDeviceId && audioInputs.length > 0) {
          setSelectedDeviceId(audioInputs[0].deviceId)
        }
        
        // Set default speaker if not already set
        if (!selectedSpeakerId && audioOutputs.length > 0) {
          setSelectedSpeakerId(audioOutputs[0].deviceId)
        }

        setDevicesLoaded(true)
      } catch (err) {
        console.error('Failed to enumerate audio devices:', err)
        setError('Failed to access microphone. Please grant permission.')
      }
    }

    loadAudioDevices()

    // Listen for device changes
    navigator.mediaDevices.addEventListener('devicechange', loadAudioDevices)

    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', loadAudioDevices)
    }
  }, [])

  // Auto-connect once devices are loaded
  useEffect(() => {
    if (devicesLoaded && audioDevices.length > 0 && !token && !serverUrl && !isConnecting && !hasAttemptedConnect.current) {
      hasAttemptedConnect.current = true
      const connect = async () => {
        setIsConnecting(true)
        setError('')
        
        try {
          const roomName = livekitService.generateRoomName(userId)
          const participantName = userId
          const { token: accessToken, url } = await livekitService.getToken(roomName, participantName, userId)
          
          setToken(accessToken)
          setServerUrl(url)
        } catch (err) {
          console.error('Failed to connect:', err)
          setError(err instanceof Error ? err.message : 'Failed to connect to LiveKit')
          setIsConnecting(false)
          hasAttemptedConnect.current = false // Allow retry on error
        }
      }
      
      connect()
    }
  }, [devicesLoaded, audioDevices.length, userId])

  const handleConnect = async () => {
    hasAttemptedConnect.current = true
    setIsConnecting(true)
    setError('')
    
    try {
      const roomName = livekitService.generateRoomName(userId)
      const participantName = userId
      const { token: accessToken, url } = await livekitService.getToken(roomName, participantName, userId)
      
      setToken(accessToken)
      setServerUrl(url)
    } catch (err) {
      console.error('Failed to connect:', err)
      setError(err instanceof Error ? err.message : 'Failed to connect to LiveKit')
      setIsConnecting(false)
      hasAttemptedConnect.current = false
    }
  }

  const handleDisconnect = () => {
    setToken('')
    setServerUrl('')
    setIsConnecting(false)
  }

  if (!token || !serverUrl) {
    return (
      <div className="voice-chat-container">
        <motion.div 
          className="voice-chat-card"
          initial={{ opacity: 0, y: 60 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {error ? (
            <>
              <motion.div className="voice-chat-header">
                <h2>Connection Failed</h2>
                <p>Unable to connect to voice chat</p>
              </motion.div>
              
              <div className="error-message">
                <p>{error}</p>
                <small>Make sure your LiveKit server is running and the backend token endpoint is accessible.</small>
              </div>
              
              <motion.button 
                onClick={handleConnect}
                className="connect-button"
              >
                <span>Retry Connection</span>
              </motion.button>
            </>
          ) : (
            <div className="voice-chat-header">
              <Loader2 className="animate-spin" size={32} style={{ margin: '0 auto 1rem' }} />
              <h2>Connecting...</h2>
              <p>Setting up your voice chat session</p>
            </div>
          )}
        </motion.div>
      </div>
    )
  }

  return (
    <div className="voice-chat-container">
      <LiveKitRoom
        token={token}
        serverUrl={serverUrl}
        connect={true}
        audio={{
          deviceId: selectedDeviceId || undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }}
        video={false}
        onDisconnected={handleDisconnect}
        className="livekit-room"
        options={{
          adaptiveStream: { pixelDensity: 'screen' },
          dynacast: true,
          publishDefaults: {
            audioPreset: {
              maxBitrate: 48000,
            },
            dtx: true,
            red: true,
          },
        }}
      >
        <AgentInterface 
          onDisconnect={handleDisconnect} 
          audioDevices={audioDevices}
          audioOutputDevices={audioOutputDevices}
          selectedDeviceId={selectedDeviceId}
          selectedSpeakerId={selectedSpeakerId}
          onDeviceChange={setSelectedDeviceId}
          onSpeakerChange={setSelectedSpeakerId}
        />
        <RoomAudioRenderer />
      </LiveKitRoom>
    </div>
  )
}

interface AgentInterfaceProps {
  onDisconnect: () => void
  audioDevices: MediaDeviceInfo[]
  audioOutputDevices: MediaDeviceInfo[]
  selectedDeviceId: string
  selectedSpeakerId: string
  onDeviceChange: (deviceId: string) => void
  onSpeakerChange: (deviceId: string) => void
}

function AgentInterface({ onDisconnect, audioDevices, audioOutputDevices, selectedDeviceId, selectedSpeakerId, onDeviceChange, onSpeakerChange }: AgentInterfaceProps) {
  const { state, audioTrack } = useVoiceAssistant()
  const { localParticipant } = useLocalParticipant()
  const [isMuted, setIsMuted] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showChat, setShowChat] = useState(false)

  // Enable microphone when component mounts
  useEffect(() => {
    const enableMicrophone = async () => {
      try {
        await localParticipant.setMicrophoneEnabled(true)
        console.log('✅ Microphone enabled successfully')
      } catch (error) {
        console.error('❌ Failed to enable microphone:', error)
      }
    }
    
    if (localParticipant) {
      enableMicrophone()
    }
  }, [localParticipant])

  const toggleMute = async () => {
    try {
      await localParticipant.setMicrophoneEnabled(isMuted)
      setIsMuted(!isMuted)
    } catch (error) {
      console.error('Failed to toggle microphone:', error)
    }
  }

  const handleDeviceChange = async (deviceId: string) => {
    try {
      await localParticipant.setMicrophoneEnabled(false)
      await localParticipant.setMicrophoneEnabled(true, { deviceId })
      onDeviceChange(deviceId)
    } catch (error) {
      console.error('Failed to change microphone:', error)
    }
  }

  const handleSpeakerChange = async (deviceId: string) => {
    try {
      const audioElements = document.querySelectorAll('audio')
      audioElements.forEach((audio) => {
        if ('setSinkId' in audio && typeof (audio as any).setSinkId === 'function') {
          (audio as any).setSinkId(deviceId).catch((err: Error) => {
            console.error('Failed to set audio sink:', err)
          })
        }
      })
      onSpeakerChange(deviceId)
    } catch (error) {
      console.error('Failed to change speaker:', error)
    }
  }

  useEffect(() => {
    if (selectedSpeakerId) {
      const audioElements = document.querySelectorAll('audio')
      audioElements.forEach((audio) => {
        if ('setSinkId' in audio && typeof (audio as any).setSinkId === 'function') {
          (audio as any).setSinkId(selectedSpeakerId).catch((err: Error) => {
            console.error('Failed to set audio sink:', err)
          })
        }
      })
    }
  }, [selectedSpeakerId])

  return (
    <motion.div 
      className="agent-interface"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div className="agent-status">
        <div className="status-indicator">
          <motion.div 
            className={`status-dot ${state}`}
            animate={{ 
              scale: state === 'speaking' ? [1, 1.2, 1] : 1,
            }}
            transition={{ 
              repeat: state === 'speaking' ? Infinity : 0, 
              duration: 0.8 
            }}
          />
          <span className="status-text">
            {state === 'listening' && 'Listening...'}
            {state === 'thinking' && 'Thinking...'}
            {state === 'speaking' && 'Speaking...'}
            {state === 'connecting' && 'Connecting...'}
            {state === 'initializing' && 'Initializing...'}
            {state === 'disconnected' && 'Disconnected'}
          </span>
        </div>
      </motion.div>

      <motion.div className="visualizer-container">
        <BarVisualizer 
          state={state}
          barCount={15}
          trackRef={audioTrack}
        />
      </motion.div>

      <motion.div className="agent-info">
        <h2>Connected to Agent</h2>
        <p>Your AI companion is ready to chat</p>
      </motion.div>

      <motion.div className="controls">
        <motion.button 
          onClick={toggleMute}
          className={`control-button ${isMuted ? 'muted' : ''}`}
          title={isMuted ? 'Unmute' : 'Mute'}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
        </motion.button>
        
        <motion.button 
          onClick={() => setShowChat(!showChat)}
          className={`control-button ${showChat ? 'active' : ''}`}
          title={showChat ? 'Hide Chat' : 'Show Chat'}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <MessageSquare size={24} />
        </motion.button>
        
        <motion.button 
          onClick={() => setShowSettings(!showSettings)}
          className={`control-button ${showSettings ? 'active' : ''}`}
          title="Settings"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Settings size={24} />
        </motion.button>
        
        <motion.button 
          onClick={onDisconnect}
          className="control-button disconnect"
          title="Disconnect"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Phone size={24} />
        </motion.button>
      </motion.div>

      <div className="settings-container">
        <AnimatePresence>
          {showSettings && (
            <motion.div
              className="settings-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSettings(false)}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {showSettings && (audioDevices.length > 0 || audioOutputDevices.length > 0) && (
            <motion.div
              className="settings-panel"
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ 
                type: 'spring',
                stiffness: 300,
                damping: 30
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="settings-header">
                <div className="settings-header-info">
                  <Settings size={20} />
                  <span>Audio Settings</span>
                </div>
                <button 
                  onClick={() => setShowSettings(false)}
                  className="settings-close-button"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="settings-content">
                {audioDevices.length > 0 && (
                  <div className="setting-item">
                    <label htmlFor="active-microphone-select">
                      <Mic size={16} />
                      <span>Microphone</span>
                    </label>
                    <select 
                      id="active-microphone-select"
                      value={selectedDeviceId}
                      onChange={(e) => handleDeviceChange(e.target.value)}
                    >
                      {audioDevices.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || `Microphone ${device.deviceId.slice(0, 8)}`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {audioOutputDevices.length > 0 && (
                  <div className="setting-item">
                    <label htmlFor="active-speaker-select">
                      <Volume2 size={16} />
                      <span>Speaker</span>
                    </label>
                    <select 
                      id="active-speaker-select"
                      value={selectedSpeakerId}
                      onChange={(e) => handleSpeakerChange(e.target.value)}
                    >
                      {audioOutputDevices.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || `Speaker ${device.deviceId.slice(0, 8)}`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AgentTextChat 
        isVisible={showChat} 
        onToggle={() => setShowChat(!showChat)} 
      />
    </motion.div>
  )
}

export default AgentVoiceChat


