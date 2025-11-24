/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// pages/index.tsx or app/page.tsx
'use client'; // Important if using the App Router

import { useState, useEffect, useRef } from 'react';
import { IconX, IconCircle, IconSquare, IconTriangle} from '@tabler/icons-react';
// Using Socket.IO client for easier WebSocket management (reconnects, etc.)
// Install with: npm install socket.io-client
// Removed Socket.IO import

// --- Configuration ---
// Now, the frontend talks to its OWN origin, and the K8s Ingress/Service
// will route requests for specific paths (like /api/start and /ws)
// to the internal Go backend service.
// Use a relative path or the frontend's own external URL.
const BASE_URL = process.env.NEXT_PUBLIC_FRONTEND_URL || ''; // Use empty string for relative path if deployed on same domain
const START_GAME_ENDPOINT = `${BASE_URL}/api/start`; // Map this path in your Ingress/proxy to the Go backend's /start
const STOP_GAME_ENDPOINT = `${BASE_URL}/api/stop`; //
// Construct WebSocket URL, replacing http(s) with ws(s)
const WEBSOCKET_URL = `${BASE_URL}/ws`.replace(/^http/, 'ws');

// Define the possible arrow keys
const ARROW_KEYS = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
const ALLOWED_KEYS = ['w', 'a', 's', 'd', 'W', 'A', 'S', 'D'];
// const ARROW_KEYS = ['ArrowUp'];

export default function GamePage() {
  // --- State Management ---
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'finished'>('idle');
  const [points, setPoints] = useState(0);
  const [replicaCount, setReplicaCount] = useState(1); // Start assuming 1 replica
  const [sequence, setSequence] = useState<string[]>([]); // The sequence user needs to press
  const [sequenceIndex, setSequenceIndex] = useState(0); // Current position in the sequence

  const gameStateRef = useRef(gameState); // Ref to hold current gameState

  // Ref for the WebSocket connection
  const socketRef = useRef<WebSocket | null>(null);

  // Update gameStateRef whenever gameState changes
  useEffect(() => {
    gameStateRef.current = gameState;
  }, [gameState]);

  // --- Game Logic Functions ---

  // Generates a random sequence of arrow keys
  const generateSequence = (length: number): string[] => {
    return Array.from({ length }, () => ARROW_KEYS[Math.floor(Math.random() * ARROW_KEYS.length)]);
  };


  const endGame = async () => {
    try {
      const response = await fetch(STOP_GAME_ENDPOINT, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      console.log('Scale down triggered!')

    } catch (error) {
      console.error('Failed to trigger scale down', error);
    }
  }

  // Handles the game start logic
  const startGame = async () => {
    setGameState('playing');
    setPoints(0);
    setReplicaCount(1); // Reset display to initial state
    setSequenceIndex(0);
    const initialSequence = generateSequence(5); // Start with a sequence of 5
    setSequence(initialSequence);

    // 1. Trigger Scale Up via Backend HTTP Endpoint (routed through frontend's URL)
    try {
      const response = await fetch(START_GAME_ENDPOINT, {
        method: 'POST',
        // Add headers if needed (e.g., for authentication)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      console.log('Scale up triggered successfully');

    } catch (error) {
      console.error('Failed to trigger scale up:', error);
      // Handle error: maybe show a message to the user and reset state
      setGameState('idle');
      return; // Stop here if the trigger failed
    }

    // 2. Establish WebSocket connection for Real-time Updates (routed through frontend's URL)
    // Socket.IO client will handle connection attempts and re-attempts
    // Establish standard WebSocket connection
    const socket = new WebSocket(WEBSOCKET_URL);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('WebSocket connected');
      // Standard WebSocket doesn't require explicit subscription messages here
      // The backend sends updates automatically upon connection and changes
    };

    // Listen for messages from the backend
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && typeof data.replicas === 'number') {
          // console.log('Received replica update:', data.replicas); // Original log
          setReplicaCount(data.replicas);

          // Check if Kubernetes scaling "won"
          if (data.replicas >= 50 && gameStateRef.current === 'playing') {
            // Add a small delay so the user sees the final count before the alert
            setTimeout(() => {
              if (gameStateRef.current === 'playing') { // Double check state in case user won points simultaneously
                setGameState('finished');
                socket.close(); // Close standard WebSocket
              }
            }, 100); // Short delay
          }
        } else {
          console.warn('Received unexpected WebSocket message format:', event.data);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error, 'Data:', event.data);
      }
    };

    socket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.reason, 'Code:', event.code);
      // Handle disconnect
      if (gameStateRef.current === 'playing') {
        // If game is ongoing and socket disconnects, it's likely an issue
        setGameState('finished');
      }
      socketRef.current = null; // Clear ref on close
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Handle connection errors
      if (gameStateRef.current === 'playing') {
        setGameState('finished'); // End game if connection fails
      }
      socketRef.current = null; // Clear ref on error
    };
  };

  // Handles user pressing an arrow key during the game
  const handleArrowKeyPress = (key: string) => {
    if (gameState !== 'playing') return; // Only process input when playing

    if (key === 'w' || key === 'W') key = 'ArrowUp';
    if (key === 'a' || key === 'A') key = 'ArrowLeft';
    if (key === 's' || key === 'S') key = 'ArrowDown';
    if (key === 'd' || key === 'D') key = 'ArrowRight';

    if (key === sequence[sequenceIndex]) {
      // Correct key pressed!
      console.log('Correct key!');
      setPoints(prevPoints => {
        const newPoints = prevPoints + 1;
        // Check if user won
        if (newPoints >= 50) {
          setGameState('finished');
          // socketRef.current?.close(); // Close standard WebSocket
        }
        return newPoints;
      });

      setSequenceIndex(prevIndex => {
        const nextIndex = prevIndex + 1;
        if (nextIndex === sequence.length) {
          // Completed the current sequence, generate a new one
          const newSeqLength = Math.min(sequence.length + 1, 15); // Gradually increase difficulty up to 15 keys
          const newSequence = generateSequence(newSeqLength);
          setSequence(newSequence);
          return 0; // Reset index for the new sequence
        }
        return nextIndex;
      });

    } else {
      // Incorrect key pressed - handle failure
      console.log('Incorrect key! Points gained in this sequence will be lost.');
      const pointsGainedThisSequence = sequenceIndex; // Capture points earned in current sequence
      setPoints(prevPoints => Math.max(0, prevPoints - pointsGainedThisSequence)); // Revoke those points
      setSequenceIndex(0); // Reset sequence progress
    }
  };

  // --- Effect Hook for Event Listeners ---
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (gameState === 'idle' && event.key === 'Enter') {
        startGame();
      } else if (gameState === 'playing' && (ARROW_KEYS.includes(event.key) || ALLOWED_KEYS.includes(event.key))) {
        handleArrowKeyPress(event.key);
      }
    };

    // Add the global keydown listener
    window.addEventListener('keydown', handleKeyDown);

    // Clean up event listener on component unmount or when dependencies change
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
    // Dependencies should include everything read by handleKeyDown and functions it calls
    // startGame and handleArrowKeyPress are defined in the component scope,
    // so they are recreated on each render. To make them stable, they could be
    // wrapped in useCallback, or we list their own underlying state dependencies here.
    // For now, listing the states directly used or affected by keydown actions:
  }, [gameState, sequence, sequenceIndex, points]); // Removed replicaCount

  // Effect for WebSocket cleanup ONLY on component unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        console.log("Component unmounting, closing WebSocket via unmount effect.");
        socketRef.current.close();
        socketRef.current = null; // Clear the ref
      }
    };
  }, []); // Empty dependency array ensures this runs only on mount and unmount

  // Effect to ensure socket is disconnected if game state changes to finished by other means
  useEffect(() => {
    if (gameState === 'finished' && socketRef.current) {
      console.log("Game finished, ensuring socket is disconnected.");
      socketRef.current.close();
      socketRef.current = null;
    }
  }, [gameState]);

  useEffect(() => {
    if(gameState === 'finished') {
      endGame();
    }
  }, [gameState])


  // --- Rendered UI ---
  return (
    <div style={{ fontFamily: 'sans-serif', textAlign: 'center', padding: '20px' }}>
      <h1>Are You Faster CoCP?</h1>

      {gameState === 'idle' && (
        <div style={{ marginTop: '50px' }}>
          <p style={{ fontSize: '4em' }}>Press <span className='bold'>Enter</span> to start the race!</p>
          <p>Compete against GKE scaling!</p>
        </div>
      )}

      {gameState === 'playing' && (
        <div style={{ marginTop: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
            {/* Player Info */}
            <div style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '8px', minWidth: '200px' }}>
              <h2 style={{ fontSize: '2em' }}>Your Points: <span style={{ color: 'green' }}>{points}</span> / 50</h2>
              <p>Press the sequence:</p>
              <div style={{ minHeight: '1.5em' }}> {/* Reserve space */}
                {sequence.map((key, index) => (
                  <span
                    key={index}
                    style={{
                      marginRight: '8px',
                      fontWeight: index === sequenceIndex ? 'bold' : 'normal',
                      color: index < sequenceIndex ? 'green' : (index === sequenceIndex ? 'blue' : 'black'),
                      fontSize: '4em'
                    }}
                  >
                    {/* Display arrow symbols or text */}
                    {key === 'ArrowUp' && <IconTriangle size={36}/>}
                    {key === 'ArrowDown' && <IconCircle size={36} />}
                    {key === 'ArrowLeft' && <IconX size={36} />}
                    {key === 'ArrowRight' && <IconSquare size={36} />}
                    {/* Or use text: {key.replace('Arrow', '')} */}
                  </span>
                ))}
              </div>
            </div>

            {/* Kubernetes Info */}
            <div style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '8px', minWidth: '200px', backgroundColor: replicaCount >= 50 ? '#fdd' : 'transparent' }}>
              <h2>Kubernetes Replicas: <span style={{ color: replicaCount >= 50 ? 'red' : 'orange' }}>{replicaCount}</span> / 50</h2>
              {replicaCount < 50 && <p>Scaling...</p>}
              {replicaCount >= 50 && <p style={{ color: 'red', fontWeight: 'bold' }}>Scale Up Complete!</p>}
            </div>
          </div>

          {/* Game Status / Win/Loss Message */}
          {points >= 50 && ( // Show temporary message before alert
            <p style={{ color: 'green', fontWeight: 'bold', fontSize: '1.5em', marginTop: '20px' }}>
              You reached 50 points! Waiting for final K8s count...
            </p>
          )}

        </div>
      )}

      {gameState === 'finished' && (
        <div style={{ marginTop: '50px' }}>
          <h2>Game Over!</h2>
          <p style={{ fontSize: '1.2em' }}>Your final score: <span style={{ fontWeight: 'bold' }}>{points}</span></p>
          <p style={{ fontSize: '1.2em' }}>Final Kubernetes replicas: <span style={{ fontWeight: 'bold' }}>{replicaCount}</span></p>
          <button
            onClick={() => setGameState('idle')}
            style={{
              marginTop: '20px',
              padding: '10px 20px',
              fontSize: '1em',
              cursor: 'pointer',
              borderRadius: '5px',
              border: 'none',
              backgroundColor: '#0070f3',
              color: 'white'
            }}
          >
            Play Again?
          </button>
        </div>
      )}

      {/* Basic Instructions */}
      <div style={{ marginTop: '40px', fontSize: '0.9em', color: '#555' }}>
        <p>Instructions: Press the arrow keys (↑, ↓, ←, →), (X, O, □, ∆) or (w, a, s, d) in the order shown to gain points.</p>
        <p>(↑ == w == ∆, ↓ == s == O, ← == a == X, → == d == □)</p>
        <p>Race to 50 points before Kubernetes scales the target application to 50 replicas!</p>
      </div>
    </div>
  );
}
