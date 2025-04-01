"use client";
import Results from "@/components/Results";

interface ResultsOverlayProps {
  showResults: boolean;
  playerOneScore: number;
  playerTwoScore: number;
  playerName: string;
}

/** 
 * Conditionally renders the <Results /> component 
 * if showResults = true 
 */
export default function ResultsOverlay({
  showResults,
  playerOneScore,
  playerTwoScore,
  playerName,
}: ResultsOverlayProps) {
  if (!showResults) return null; // Hide if not showing results

  return (
    <Results
      playerOneScore={playerOneScore}
      playerTwoScore={playerTwoScore}
      playerName={playerName}
    />
  );
}
