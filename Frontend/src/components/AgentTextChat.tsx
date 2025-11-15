import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, MessageSquare, X, Bot, User } from 'lucide-react'
import { 
  useChat,
  useLocalParticipant,
  ReceivedChatMessage 
} from '@livekit/components-react'
import './AgentTextChat.css'

interface AgentTextChatProps {
  isVisible: boolean
  onToggle: () => void
  className?: string
}

function AgentTextChat({ isVisible, onToggle }: AgentTextChatProps) {
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const { send: sendChatMessage, chatMessages } = useChat()
  const { localParticipant } = useLocalParticipant()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (messagesEndRef.current && isVisible) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatMessages, isVisible])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isSending) return

    setIsSending(true)
    try {
      await sendChatMessage(message.trim())
      setMessage('')
    } catch (error) {
      console.error('Failed to send message:', error)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  const formatMessage = (msg: ReceivedChatMessage) => {
    const isFromAgent = msg.from?.identity !== localParticipant?.identity
    const timestamp = new Date(msg.timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })

    return {
      id: `${msg.from?.identity}-${msg.timestamp}`,
      text: msg.message,
      isFromAgent,
      timestamp,
      sender: isFromAgent ? 'Agent' : 'You'
    }
  }

  const formattedMessages = chatMessages.map(formatMessage)

  return (
    <div className="text-chat-container">
      <AnimatePresence>
        {isVisible && (
          <motion.div
            className="chat-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isVisible && (
          <motion.div
            className="text-chat-panel"
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
            <div className="chat-header">
              <div className="chat-header-info">
                <MessageSquare size={18} />
                <span>Text Chat</span>
              </div>
              <button 
                onClick={onToggle}
                className="chat-close-button"
              >
                <X size={16} />
              </button>
            </div>

            <div className="chat-messages">
              <AnimatePresence mode="popLayout">
                {formattedMessages.length === 0 ? (
                  <div className="empty-chat">
                    <MessageSquare size={32} />
                    <p>Start typing to chat with the agent!</p>
                    <small>Your messages will be sent alongside voice input.</small>
                  </div>
                ) : (
                  formattedMessages.map((msg) => (
                    <motion.div
                      key={msg.id}
                      className={`chat-message ${msg.isFromAgent ? 'agent-message' : 'user-message'}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                    >
                      <div className="message-avatar">
                        {msg.isFromAgent ? (
                          <Bot size={16} />
                        ) : (
                          <User size={16} />
                        )}
                      </div>
                      <div className="message-content">
                        <div className="message-header">
                          <span className="message-sender">{msg.sender}</span>
                          <span className="message-timestamp">{msg.timestamp}</span>
                        </div>
                        <div className="message-text">{msg.text}</div>
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>

              <div ref={messagesEndRef} />
            </div>

            <form 
              onSubmit={handleSendMessage}
              className="chat-input-form"
            >
              <div className="chat-input-container">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  className="chat-input"
                  rows={1}
                  disabled={isSending}
                />
                <motion.button
                  type="submit"
                  className={`chat-send-button ${(!message.trim() || isSending) ? 'disabled' : ''}`}
                  disabled={!message.trim() || isSending}
                  whileHover={{ scale: (!message.trim() || isSending) ? 1 : 1.05 }}
                  whileTap={{ scale: (!message.trim() || isSending) ? 1 : 0.95 }}
                >
                  <Send size={16} />
                </motion.button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default AgentTextChat

