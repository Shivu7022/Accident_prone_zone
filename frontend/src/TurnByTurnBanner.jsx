import React, { useEffect, useRef } from "react";
import "./TurnByTurnBanner.css";

export default function TurnByTurnBanner({
  currentStep,
  nextStep,
  distanceToManeuver,
  audioEnabled = true,
}) {
  const lastSpokenRef = useRef("");

  // Text to speech voice synthesis
  useEffect(() => {
    if (!audioEnabled || !currentStep || !window.speechSynthesis) return;

    const instructionText = currentStep.instruction || currentStep.name || "";
    if (instructionText && instructionText !== lastSpokenRef.current) {
      lastSpokenRef.current = instructionText;

      try {
        window.speechSynthesis.cancel(); // Stop current speaking
        const utterance = new SpeechSynthesisUtterance(instructionText);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        console.warn("Speech synthesis error", e);
      }
    }
  }, [currentStep, audioEnabled]);

  if (!currentStep) return null;

  // Determine maneuver icon
  const getManeuverIcon = (modifier, type) => {
    const mod = (modifier || "").toLowerCase();
    const typ = (type || "").toLowerCase();

    if (mod.includes("left") || mod.includes("slight left") || mod.includes("sharp left")) {
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="maneuver-svg">
          <path d="M14 6l-6 6 6 6V6z" />
          <path d="M12 12h7v6h-2v-4h-5v-2z" />
        </svg>
      );
    }
    if (mod.includes("right") || mod.includes("slight right") || mod.includes("sharp right")) {
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="maneuver-svg">
          <path d="M10 6l6 6-6 6V6z" />
          <path d="M12 12H5v6h2v-4h5v-2z" />
        </svg>
      );
    }
    if (typ.includes("arrive") || typ.includes("destination")) {
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="maneuver-svg dest-svg">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
        </svg>
      );
    }
    if (typ.includes("roundabout")) {
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className="maneuver-svg">
          <path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 18a8 8 0 118-8 8 8 0 01-8 8z" />
          <path d="M12 6v4l3-3-3-1z" />
        </svg>
      );
    }
    // Default straight arrow
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="maneuver-svg">
        <path d="M12 4l-6 6h4v10h4V10h4l-6-6z" />
      </svg>
    );
  };

  const formatDistance = (meters) => {
    if (meters === undefined || meters === null) return "";
    if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
    return `${Math.round(meters)} m`;
  };

  return (
    <div className="turn-banner-card">
      <div className="turn-main-section">
        <div className="maneuver-icon-container">
          {getManeuverIcon(currentStep.modifier, currentStep.type)}
        </div>

        <div className="turn-instruction-info">
          <div className="distance-countdown">
            {formatDistance(distanceToManeuver ?? currentStep.distance)}
          </div>
          <div className="instruction-text">
            {currentStep.instruction || `Continue on ${currentStep.name || "current road"}`}
          </div>
        </div>
      </div>

      {nextStep && (
        <div className="turn-next-preview">
          <span className="next-label">THEN</span>
          <span className="next-text">
            {nextStep.instruction || `In ${formatDistance(nextStep.distance)}, ${nextStep.name || "turn"}`}
          </span>
        </div>
      )}
    </div>
  );
}
