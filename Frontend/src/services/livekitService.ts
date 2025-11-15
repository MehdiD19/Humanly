// LiveKit Service for token generation and room management

const LIVEKIT_API_URL = import.meta.env.VITE_LIVEKIT_URL || 'ws://localhost:7880'
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

interface TokenResponse {
  token: string
  url: string
}

export class LiveKitService {
  /**
   * Get a LiveKit access token for the user
   * This makes a request to your backend to generate a token
   */
  async getToken(roomName: string, participantName: string, userId?: string): Promise<TokenResponse> {
    try {
      const response = await fetch(`${BACKEND_URL}/api/livekit-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room_name: roomName,
          participant_name: participantName,
          user_id: userId,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to get LiveKit token' }))
        throw new Error(errorData.error || 'Failed to get LiveKit token from backend')
      }

      const data = await response.json()

      return {
        token: data.token,
        url: LIVEKIT_API_URL,
      }
    } catch (error) {
      console.error('Error getting LiveKit token:', error)
      throw error
    }
  }

  /**
   * Generate a unique room name for a user session
   */
  generateRoomName(userId: string): string {
    const timestamp = Date.now()
    return `user-${userId}-${timestamp}`
  }
}

export const livekitService = new LiveKitService()


