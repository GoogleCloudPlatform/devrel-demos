'use client'

import { useEffect, useState } from "react";
import { checkSecretPasswordExists } from "./actions";
import Play from "@/components/Play";
import { Canvas } from '@react-three/fiber'
import MessagePretty from "@/components/MessagePretty";
import StartButton from "@/components/StartButton";

export default function Home() {
  const [secretPassword, setSecretPassword] = useState<string>((typeof window !== 'undefined' && localStorage.getItem("secretPassword")) || '');
  const [secretPasswordExists, setSecretPasswordExists] = useState<boolean>(false);
  const [showPassword, setShowPassword] = useState<boolean>(secretPasswordExists && !secretPassword);
  const [showPlayComponent, setShowPlayComponent] = useState<boolean>(false);

  const setPassword = (event: { target: { value: string; }; }) => {
    const newValue = event.target.value;
    localStorage.setItem('secretPassword', newValue);
    setSecretPassword(newValue);
  }

  const handleShowPasswordClick = () => {
    setSecretPassword('');
    setShowPassword(true);
  }

  useEffect(() => {
    const checkPasswordExists = async () => {
      const passwordExists = await checkSecretPasswordExists();
      setSecretPasswordExists(passwordExists);
    }
    checkPasswordExists();
  }, []);

  if (showPlayComponent) {
    return (
      <Play />
    );
  }

  const colors = ['#EA4335', '#34A853','#FBBC04', '#4285F4'];
  const playerOneBlocks = Array.from(Array(100).keys()).map((index) => {
    const color = colors[Math.floor(Math.random() * colors.length)];
    const randomNumber = Math.random() - 0.5;
    const xPosition = randomNumber * 10;
    const yPosition = (index / 5) + randomNumber;
    const uuid = crypto.randomUUID();
    return { randomNumber, xPosition, yPosition, uuid, color }
  });


  return (
    <>
      <div className="absolute min-h-screen top-0 bottom-0 left-0 right-0 -z-10">
        <Canvas>
          <ambientLight intensity={Math.PI / 2} />
          <pointLight position={[-10, -10, -10]} decay={0} intensity={2} />
          <pointLight position={[5, 5, 5]} decay={0} intensity={3} />
          {playerOneBlocks.map(({ randomNumber, xPosition, yPosition, uuid, color }) => {
            return (
              <MessagePretty
                key={uuid}
                position={[xPosition, yPosition, -3]}
                endPoint={[randomNumber,0,0]}
                color={color}
              />
            )
          })}
        </Canvas>
      </div>
      <main className="flex flex-col min-h-screen items-center justify-between p-24">
        <h1 className={`mb-3 text-7xl font-mono -z-20`}>
          Load Balancing Blitz
        </h1>
        <StartButton
          onClick={() => setShowPlayComponent(true)}
          showPassword={showPassword}
        />
        <div>
          <p>
            Press 1, 2, 3, and 4 to distribute the incoming requests
            across the four virtual machines.
          </p>
          <p>
            Hint: Keep moving! Be careful not to direct all of the requests to a single machine.
          </p>
        </div>
        {secretPasswordExists && <>
          {showPassword ? <div>
            <input value={secretPassword} onChange={setPassword} className="border border-black border-1" />
            <button onClick={() => setShowPassword(false)}>
              Hide Password
            </button>
          </div>
            : <button onClick={handleShowPasswordClick}>
              Enter Password
            </button>
          }
        </>}
      </main>
    </>
  );
}
