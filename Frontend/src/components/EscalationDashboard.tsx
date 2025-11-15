import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, AlertCircle } from "lucide-react";
import "./EscalationDashboard.css";

interface Escalation {
  escalation_id: string;
  room_name: string;
  user_id: string;
  reason: string;
  urgency: "low" | "medium" | "high" | "critical";
  decision_type: string;
  context_details: string;
  recent_transcript: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
  status: "pending" | "resolved";
  created_at: string;
  human_response?: string;
  responded_at?: string;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function EscalationDashboard() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [selectedEscalation, setSelectedEscalation] =
    useState<Escalation | null>(null);
  const [responseText, setResponseText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("disconnected");
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    const wsUrl = API_BASE_URL.replace("http://", "ws://").replace(
      "https://",
      "wss://"
    );
    const ws = new WebSocket(`${wsUrl}/ws/frontend`);

    ws.onopen = () => {
      console.log("✅ Connected to WebSocket");
      setConnectionStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "initial_state") {
          setEscalations(data.escalations || []);
        } else if (data.type === "new_escalation") {
          setEscalations((prev) => {
            const exists = prev.find(
              (e) => e.escalation_id === data.escalation.escalation_id
            );
            if (exists) return prev;
            return [data.escalation, ...prev];
          });
        } else if (data.type === "escalation_resolved") {
          setEscalations((prev) =>
            prev.map((e) =>
              e.escalation_id === data.escalation_id ? data.escalation : e
            )
          );
          if (selectedEscalation?.escalation_id === data.escalation_id) {
            setSelectedEscalation(data.escalation);
          }
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnectionStatus("disconnected");
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
      setConnectionStatus("disconnected");
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        setConnectionStatus("connecting");
      }, 3000);
    };

    wsRef.current = ws;

    // Load initial escalations via HTTP
    fetchPendingEscalations();

    return () => {
      ws.close();
    };
  }, []);

  const fetchPendingEscalations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/escalations/pending`);
      const data = await response.json();
      setEscalations(data.escalations || []);
    } catch (error) {
      console.error("Error fetching escalations:", error);
    }
  };

  const handleSelectEscalation = async (escalation: Escalation) => {
    if (escalation.escalation_id === selectedEscalation?.escalation_id) {
      setSelectedEscalation(null);
      setResponseText("");
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/escalations/${escalation.escalation_id}`
      );
      const fullEscalation = await response.json();
      setSelectedEscalation(fullEscalation);
      setResponseText("");
    } catch (error) {
      console.error("Error fetching escalation details:", error);
    }
  };

  const handleSubmitResponse = async () => {
    if (!selectedEscalation || !responseText.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/escalations/${selectedEscalation.escalation_id}/respond`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            response_text: responseText.trim(),
          }),
        }
      );

      if (response.ok) {
        setResponseText("");
        setSelectedEscalation(null);
        await fetchPendingEscalations();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || "Failed to submit response"}`);
      }
    } catch (error) {
      console.error("Error submitting response:", error);
      alert("Failed to submit response. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const pendingEscalations = escalations.filter((e) => e.status === "pending");

  return (
    <div className="escalation-container">
      <motion.div
        className="escalation-content"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <motion.div
          className="escalation-header"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <h1>Escalation Dashboard</h1>
          <p>Monitor and respond to agent escalations in real-time</p>
          <div className="connection-status">
            <div
              className={`status-dot ${
                connectionStatus === "connected"
                  ? "connected"
                  : connectionStatus === "connecting"
                  ? "connecting"
                  : "disconnected"
              }`}
            />
            <span className="status-text">
              {connectionStatus === "connected"
                ? "Connected"
                : connectionStatus === "connecting"
                ? "Connecting..."
                : "Disconnected"}
            </span>
          </div>
        </motion.div>

        {!selectedEscalation ? (
          <motion.div
            className="escalations-grid"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            {pendingEscalations.length === 0 ? (
              <div className="empty-state">
                <AlertCircle
                  size={48}
                  style={{
                    margin: "0 auto 1rem",
                    color: "var(--text-gray-400)",
                  }}
                />
                <p>No pending escalations</p>
              </div>
            ) : (
              pendingEscalations.map((escalation) => (
                <motion.div
                  key={escalation.escalation_id}
                  className="escalation-card"
                  onClick={() => handleSelectEscalation(escalation)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="escalation-card-header">
                    <span
                      className={`urgency-badge urgency-${escalation.urgency}`}
                    >
                      {escalation.urgency}
                    </span>
                    <span className="escalation-time">
                      {new Date(escalation.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="escalation-type">
                    {escalation.decision_type.replace("_", " ")}
                  </div>
                  <p className="escalation-reason">{escalation.reason}</p>
                  <div className="escalation-meta">
                    Room: {escalation.room_name} • User:{" "}
                    {escalation.user_id.slice(0, 8)}...
                  </div>
                </motion.div>
              ))
            )}
          </motion.div>
        ) : (
          <motion.div
            className="response-panel"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="response-card">
              <h2>Respond to Escalation</h2>

              <div className="response-section">
                <label>Reason</label>
                <p>{selectedEscalation.reason}</p>
              </div>

              {selectedEscalation.context_details && (
                <div className="response-section">
                  <label>Context Details</label>
                  <p>{selectedEscalation.context_details}</p>
                </div>
              )}

              {selectedEscalation.recent_transcript &&
                selectedEscalation.recent_transcript.length > 0 && (
                  <div className="response-section">
                    <label>Recent Conversation</label>
                    <div className="transcript-box">
                      {selectedEscalation.recent_transcript.map((msg, idx) => (
                        <div key={idx} className="transcript-message">
                          <span className="transcript-role">
                            {msg.role === "user" ? "User" : "Agent"}:
                          </span>
                          <span className="transcript-content">
                            {msg.content}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <span
                  className={`urgency-badge urgency-${selectedEscalation.urgency}`}
                >
                  {selectedEscalation.urgency}
                </span>
                <span
                  className="urgency-badge"
                  style={{
                    background: "var(--bg-gray-100)",
                    color: "var(--text-gray-700)",
                  }}
                >
                  {selectedEscalation.decision_type.replace("_", " ")}
                </span>
              </div>

              {selectedEscalation.status === "pending" ? (
                <div className="response-section">
                  <label>Your Response</label>
                  <textarea
                    value={responseText}
                    onChange={(e) => setResponseText(e.target.value)}
                    placeholder="Type your response here. This will be sent to the agent..."
                    className="response-textarea"
                  />
                  <motion.button
                    className="submit-button"
                    onClick={handleSubmitResponse}
                    disabled={!responseText.trim() || isSubmitting}
                    whileHover={{ scale: isSubmitting ? 1 : 1.02 }}
                    whileTap={{ scale: isSubmitting ? 1 : 0.98 }}
                  >
                    {isSubmitting ? "Submitting..." : "Submit Response"}
                  </motion.button>
                </div>
              ) : (
                <div className="resolved-badge">
                  <p>✓ Resolved</p>
                  {selectedEscalation.human_response && (
                    <p style={{ marginTop: "0.5rem" }}>
                      Response: {selectedEscalation.human_response}
                    </p>
                  )}
                </div>
              )}

              <motion.button
                className="back-button"
                onClick={() => {
                  setSelectedEscalation(null);
                  setResponseText("");
                }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <ArrowLeft size={18} />
                Back to List
              </motion.button>
            </div>
          </motion.div>
        )}

        <motion.button
          className="back-button"
          onClick={() => {
            window.location.href = window.location.pathname.replace(
              "?mode=dashboard",
              ""
            );
          }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <ArrowLeft size={18} />
          Back to Home
        </motion.button>
      </motion.div>
    </div>
  );
}