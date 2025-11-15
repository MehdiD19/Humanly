import { useState } from "react";
import AgentVoiceChat from "./components/AgentVoiceChat";
import LandingPage from "./components/LandingPage";
import EscalationDashboard from "./components/EscalationDashboard";

function App() {
  // Check if we're in dashboard mode (via URL or localStorage)
  const [viewMode, setViewMode] = useState<"chat" | "dashboard">(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get("mode");
    if (mode === "dashboard") return "dashboard";
    return "chat";
  });

  // For demo purposes, use a simple user ID
  // In production, this would come from authentication
  const [userId] = useState(() => {
    // Generate or retrieve user ID (could be from localStorage, auth, etc.)
    const stored = localStorage.getItem("userId");
    if (stored) return stored;
    const newId = `user_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    localStorage.setItem("userId", newId);
    return newId;
  });

  const [hasStarted, setHasStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleStart = () => {
    setIsLoading(true);
    // Small delay to show loading state
    setTimeout(() => {
      setHasStarted(true);
      setIsLoading(false);
    }, 500);
  };

  // Show dashboard if mode is dashboard
  if (viewMode === "dashboard") {
    return <EscalationDashboard />;
  }

  return (
    <div style={{ width: "100vw", minHeight: "100vh", overflow: "hidden" }}>
      {!hasStarted ? (
        <LandingPage onStart={handleStart} isLoading={isLoading} />
      ) : (
        <AgentVoiceChat userId={userId} userName="User" />
      )}
    </div>
  );
}

export default App;
