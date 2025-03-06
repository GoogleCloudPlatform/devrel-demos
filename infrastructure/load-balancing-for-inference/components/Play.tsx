"use client";

import { generatePlayerName } from "@/utils/name-generator";
import { Line } from "@react-three/drei";
import { Canvas, useLoader } from "@react-three/fiber";
import localFont from 'next/font/local';
import { memo, useEffect, useRef, useState } from "react";
import { TextureLoader } from "three";
import GpuGroup from "./GpuGroup";
const MessagePath = memo(Line);

import Player1 from "./Player1";
import Player2 from "./Player2";

import CountdownOverlay from "./CountdownOverlay";
import GpuGroupRight from "./GpuGroupRight";
import ResultsOverlay from "./ResultsOverlay";

// Load Jersey15 font
const jersey15 = localFont({
  src: '../public/fonts/Jersey15-Regular.ttf',
  variable: '--font-jersey15'
});

const totalGameTime = 60;
const player1VmXPositions = [-5.0, -3.3, -2.0, -0.6];
const player2VmXPositions = player1VmXPositions
  .map((xPosition) => -1 * xPosition)
  .reverse();
  
const vmYPosition = -1.7;
const vmYPositionTop = vmYPosition + 0.5;
const vmYPositionBottom = vmYPosition - 0.6;
const playerEndPositions: [number, number, number][] = player1VmXPositions.map(
  (xPosition) => [xPosition, vmYPositionBottom, 0]
);
const loadBalancerXPosition = -2.9;
const loadBalancerYPosition = vmYPositionTop + 2;
const playerMidYPosition = loadBalancerYPosition;

const playerOneLoadBalancerPosition: [number, number, number] = [
  loadBalancerXPosition,
  loadBalancerYPosition,
  0,
];
const lineOneStart: [number, number, number] = [
  playerOneLoadBalancerPosition[0],
  playerOneLoadBalancerPosition[1] + 0.3,
  playerOneLoadBalancerPosition[2],
];
const playerTwoLoadBalancerPosition: [number, number, number] = [
  -loadBalancerXPosition,
  loadBalancerYPosition,
  0,
];
const lineTwoStart: [number, number, number] = [
  playerTwoLoadBalancerPosition[0],
  playerTwoLoadBalancerPosition[1] + 0.3,
  playerTwoLoadBalancerPosition[2],
];

const startingBoxZ = -7;

const colors = {
  utilization: "#FFFFFF",
  black: "#202124",
  red: "#EA4335",
  green: "#34A853",
  player1: "#FBBC04",
  player2: "#4285F4",
};

const playerOneBlocks = Array.from(Array(50).keys()).map((index) => {
  const randomNumber = Math.random() - 0.5;
  const yPosition = 15 + index * 0.5 + randomNumber;
  const uuid = crypto.randomUUID();
  return {
    xPosition: loadBalancerXPosition + randomNumber, // Fixed starting X position
    yPosition,
    uuid,
  };
});

const playerTwoBlocks = Array.from(Array(50).keys()).map((index) => {
  const randomNumber = Math.random() - 0.5;
  const xPosition = -loadBalancerXPosition + randomNumber;
  const yPosition = index / 2 + 7 + randomNumber;
  const uuid = crypto.randomUUID();
  return { xPosition, yPosition, uuid };
});

type VmStatus = {
  cpu: number;
  memory: number;
  score: number;
  hostName: string;
  queue: number;
  tasksCompleted: number;
  tasksRegistered: number;
  utilization: number;
  atMaxCapacity: boolean;
};

type VmStats = {
  statusArray: VmStatus[];
  playerName: string;
  gameVmSelection: string;
  gameVmSelectionIndex: number;
  gameVmSelectionUpdates: number;
  playerOneScore: number;
  playerTwoScore: number;
};

const defaultVmStatuses: VmStatus[] = Array.from(Array(8).keys()).map(() => ({
  cpu: 0,
  memory: 11.5,
  hostName: "vm-default",
  score: 0,
  queue: 0,
  tasksCompleted: 0,
  tasksRegistered: 0,
  utilization: 0,
  atMaxCapacity: false,
}));

const defaultVmStats = {
  statusArray: defaultVmStatuses,
  playerName: "Default Player Name",
  gameVmSelection: "vm-default",
  gameVmSelectionIndex: 0,
  gameVmSelectionUpdates: 0,
  playerOneScore: 0,
  playerTwoScore: 0,
};

type ResultBlock = {
  uid: string;
  startingPosition: [number, number, number];
};

type FailResultBlock = {
  uid: string;
  startingPosition: [number, number, number];
  side: "LEFT" | "RIGHT";
};

const gpuXPositions = [...player1VmXPositions, ...player2VmXPositions];

// Define the base position of the robot on the rail
const robotBasePosition: [number, number, number] = [3.0, 1.0, 0]; // Adjust as needed

export default function Play() {

  // New GPU positions for each player.
const player1GpuPositions = [-4.90, -3.69, -2.52, -1.31];
const player2GpuPositions = [1.19, 2.43, 3.64, 4.86];


  const totalGameTime = 60;


  const [robotTargetX, setRobotTargetX] = useState(3.2);
  const [isGripping, setIsGripping] = useState(false);


  // TODO: Add pseudonyms for users
  const [playerOneEnd, setPlayerOneEnd] = useState<[number, number, number]>(
    playerEndPositions[0]
  );
  const [timeElapsed, setTimeElapsed] = useState(-5);
  const [quarterSecondCounter, setQuarterSecondCounter] = useState(0);
  const [playerName, setPlayerName] = useState("You are the...");
  const [failBlocks, setFailBlocks] = useState<FailResultBlock[]>([]);
  const [successBlocks, setSuccessBlocks] = useState<ResultBlock[]>([]);
  const [vmStats, setVmStats] = useState<VmStats>(defaultVmStats);
  const [playerTwoTotal, setTotalPlayerTwoTotal] = useState(0);
  const [gameStarted, setGameStarted] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const [blocks, setBlocks] = useState<
    {
      uuid: string;
      gpuIndex: number;
      stackPosition: number; // NEW: Tracks stacking inside GPU
    }[]
  >([]);

  const userBoxTexture = useLoader(TextureLoader, "/assets/user-box.png");
  const userFunnelTexture = useLoader(TextureLoader, "/assets/user-funnel.png");
  const yellowDataBlockTexture = useLoader(
    TextureLoader,
    "/assets/yellow-datablock.png"
  );

  // ✅ Define Robot Position Variables

  const robotGripperPosition: [number, number, number] = [3.0, -0.2, 0]; // Gripper at the end of Arm 2

  // ✅ Load Textures
  const baseTexture = useLoader(TextureLoader, "/assets/base.png");
  const arm1Texture = useLoader(TextureLoader, "/assets/arm1.png");
  const arm2Texture = useLoader(TextureLoader, "/assets/arm2.png");
  const railTexture = useLoader(TextureLoader, "/assets/rail.png");
  const gripperTexture = useLoader(TextureLoader, "/assets/gripper.png");

  // Blue side assets

const player2FunnelXPositions = [1.2, 2.4, 3.6, 4.8];
const [player2FunnelX, setPlayer2FunnelX] = useState(player2FunnelXPositions[0]);
const playerTwoActiveRef = useRef<number>(0);



useEffect(() => {
  const interval = setInterval(() => {
    const randomIndex = Math.floor(Math.random() * player2FunnelXPositions.length);
    setPlayer2FunnelX(player2FunnelXPositions[randomIndex]);
  }, 500); // update every 0.5 seconds for a faster funnel movement
  return () => clearInterval(interval);
}, []);


  // ✅ Define Robot Base Position
  const robotBasePosition: [number, number, number] = [.0, 1.0, 0];

  // ✅ Define Arm Positions Relative to Base
  const robotArm1Position: [number, number, number] = [
    robotBasePosition[0],
    robotBasePosition[1] - 0.5,
    0,
  ];
  const robotArm2Position: [number, number, number] = [
    robotArm1Position[0],
    robotArm1Position[1] - 0.5,
    0,
  ];

  // ✅ Define Rail Position
  const railPosition: [number, number, number] = [3.0, 0.5, 0];

  const userFunnelBaseY = 0.09; // ✅ Base Y-position for funnel (adjust as needed)

  // ✅ Define Constants for UserBox & UserFunnel Positioning

  const userFunnelBasePosition: [number, number, number] = [
    player1VmXPositions[0],
    userFunnelBaseY,
    0,
  ]; // ✅ Moves based on keypress

  // calculated values based on variables
  const [activeGpuIndex, setActiveGpuIndex] = useState(0);

  const playerOneMid: [number, number, number] = [
    playerOneEnd[0],
    playerMidYPosition,
    0,
  ];
  const player2NextVmIndex = playerTwoTotal % 4;
  const player2NextXPosition = player2VmXPositions[player2NextVmIndex];
  const playerTwoEnd: [number, number, number] = [
    player2NextXPosition,
    vmYPositionBottom,
    0,
  ];
  const playerTwoMid: [number, number, number] = [
    playerTwoEnd[0],
    playerMidYPosition,
    0,
  ];
  const playerOneActiveVmIndex = activeGpuIndex; // Use activeGpuIndex instead of finding position
  const playerOneAtMaxCapacity =
    vmStats.statusArray[playerOneActiveVmIndex].atMaxCapacity;
  const playerOneActiveVmId = playerOneActiveVmIndex + 1;

  const playerTwoActiveVmIndex = player2VmXPositions.reduce((bestIndex, pos, i) => {
    return Math.abs(pos - player2FunnelX) < Math.abs(player2VmXPositions[bestIndex] - player2FunnelX)
      ? i
      : bestIndex;
  }, 0);
  
  
  const playerTwoAtMaxCapacity =
    vmStats.statusArray[playerTwoActiveVmIndex + 4].atMaxCapacity;
  const playerOneScore = timeElapsed < 1 ? 0 : vmStats.playerOneScore;
  const playerTwoScore = timeElapsed < 1 ? 0 : vmStats.playerTwoScore;
  const timeRemaining = Math.min(totalGameTime - timeElapsed, totalGameTime);

  useEffect(() => {
    // add success block to any vm that has more than 0% in the queue
    const newSuccessXPosition = [];
    // add player one success block
    if (vmStats.statusArray[player2NextVmIndex].queue > 0) {
      newSuccessXPosition.push(player1VmXPositions[player2NextVmIndex]);
    }
    // add player two success block
    if (vmStats.statusArray[player2NextVmIndex + 4].queue > 0) {
      newSuccessXPosition.push(player2VmXPositions[player2NextVmIndex]);
    }
    const newSuccessBlocks = newSuccessXPosition.map((xPosition) => {
      const startingPosition: [number, number, number] = [
        xPosition,
        vmYPosition + 0.42,
        -0.5,
      ];
      const uid = crypto.randomUUID();
      return { uid, startingPosition };
    });
    // limit to 100 blocks to prevent the screen from freezing up
    setSuccessBlocks([...newSuccessBlocks, ...successBlocks].slice(0, 20));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [player2NextVmIndex]);

  useEffect(() => {
    const getStartLoader = async (playerName: string) => {
      try {
        setPlayerName(playerName);
      } catch (error) {
        console.error("Failed to start");
      }
    };
    if (!gameStarted && timeElapsed > -2) {
      setGameStarted(true);
      getStartLoader(playerName);
    }
  }, [gameStarted, playerName, timeElapsed]);

  useEffect(() => {
    const getVMStatus = async () => {
      if (timeElapsed < totalGameTime + 5) {
        // During GET READY (timeElapsed < 0), force GPU utilizations to 0.
        if (timeElapsed < 0) {
          const resetStats = {
            ...vmStats,
            statusArray: vmStats.statusArray.map((vm) => ({ ...vm, utilization: 0 })),
            playerOneScore: 0,
            playerTwoScore: 0,
          };
          setVmStats(resetStats);
          return;
        }
        
        // Compute active right GPU index based on player2FunnelX:
        const playerTwoActiveVmIndex = player2GpuPositions.reduce((bestIndex, pos, i) => {
          return Math.abs(pos - player2FunnelX) < Math.abs(player2GpuPositions[bestIndex] - player2FunnelX)
            ? i
            : bestIndex;
        }, 0);
        
        // Update rates:
        const leftSideIncreaseRate = 0.035;
        const leftSideDecreaseRate = 0.01;
        const rightSideIncreaseRate = 0.08; // Increased active fill rate for right side
        const rightSideDecreaseRate = 0.02; // Decreased drain rate for inactive right GPUs
  
        const updatedVmStats = {
          ...vmStats,
          statusArray: vmStats.statusArray.map((vmDetails, index) => {
            if (index < 4) {
              // Left side GPUs.
              if (index === playerOneActiveVmIndex) {
                return {
                  ...vmDetails,
                  utilization: Math.min(
                    vmDetails.utilization + leftSideIncreaseRate,
                    1
                  ),
                };
              } else {
                return {
                  ...vmDetails,
                  utilization: Math.max(vmDetails.utilization - leftSideDecreaseRate, 0),
                };
              }
            } else {
              // Right side GPUs (indices 4–7): compare (index - 4) with playerTwoActiveVmIndex.
              if ((index - 4) === playerTwoActiveVmIndex) {
                return {
                  ...vmDetails,
                  utilization: Math.min(vmDetails.utilization + rightSideIncreaseRate, 1),
                };
              } else {
                return {
                  ...vmDetails,
                  utilization: Math.max(vmDetails.utilization - rightSideDecreaseRate, 0),
                };
              }
            }
          }),
          playerOneScore:
            vmStats.playerOneScore +
            vmStats.statusArray.slice(0, 4).reduce((agg, vm) => agg + (vm.utilization > 0 ? 1 : 0), 0),
          playerTwoScore:
            vmStats.playerTwoScore +
            vmStats.statusArray.slice(4).reduce((agg, vm) => agg + (vm.utilization > 0 ? 1 : 0), 0),
          playerOneAtMaxCapacity: vmStats.statusArray[playerOneActiveVmIndex].utilization >= 1,
          playerTwoAtMaxCapacity:
            vmStats.statusArray[playerTwoActiveVmIndex + 4].utilization >= 1,
        };
  
        setVmStats(updatedVmStats);
      }
    };
    getVMStatus();
  }, [quarterSecondCounter, timeElapsed, player2FunnelX]);
  
  

  

  // ✅ Define Constants for UserBox & UserFunnel Positioning
  // const userBoxPosition: [number, number, number] = [-2.9, 1.2, 0]; // ✅ Fixed position

  // ✅ State to Track Funnel Movement (Moves Horizontally)
  const [userFunnelPosition, setUserFunnelPosition] = useState<
    [number, number, number]
  >([
    player1VmXPositions[0], // Starts at GPU 1
    userFunnelBaseY, // Using the new base Y position
    0,
  ]);

  // Add activeGpuIndex state to track which GPU is currently selected

  // Update the handleKeyDown function in your useEffect
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      let newXPosition: number | null = null;
      let newGpuIndex: number = activeGpuIndex;

      switch (event.code) {
        case "Digit1":
          newXPosition = player1VmXPositions[0];
          newGpuIndex = 0;
          break;
        case "Digit2":
          newXPosition = player1VmXPositions[1];
          newGpuIndex = 1;
          break;
        case "Digit3":
          newXPosition = player1VmXPositions[2];
          newGpuIndex = 2;
          break;
        case "Digit4":
          newXPosition = player1VmXPositions[3];
          newGpuIndex = 3;
          break;
        default:
          break;
      }
      if (newXPosition !== null) {
        setUserFunnelPosition([newXPosition, userFunnelBaseY, 0]);
        setActiveGpuIndex(newGpuIndex);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const playerName = generatePlayerName();
    setPlayerName(playerName);
  }, []);

  useEffect(() => {
    //Implementing the setInterval method
    const interval = setInterval(() => {
      setTimeElapsed(timeElapsed + 1);
    }, 1000);

    //Clearing the interval
    return () => clearInterval(interval);
  }, [timeElapsed]);

  useEffect(() => {
    //Implementing the setInterval method
    const fastInterval = setInterval(() => {
      setQuarterSecondCounter(quarterSecondCounter + 1);
    }, 250);

    //Clearing the interval
    return () => clearInterval(fastInterval);
  }, [quarterSecondCounter]);

  useEffect(() => {
    if (timeElapsed >= totalGameTime && !showResults) {
      setShowResults(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeElapsed]);

  const addFailBlock = (
    failBlockStartingPosition: [number, number, number]
  ) => {
    const [x, y, z] = failBlockStartingPosition;
    if (x < 0) {
      const audio = new Audio("/beep.wav");
      audio.volume = 0.1;
      // audio.play();
    } else {
      setTotalPlayerTwoTotal(playerTwoTotal + 1);
    }
    const startingPosition: [number, number, number] = [
      x + Math.random() / 4 - 0.1,
      y,
      z,
    ];
    const uid = crypto.randomUUID();
    const side: "LEFT" | "RIGHT" = ["LEFT", "RIGHT"][
      Math.floor(Math.random() * 2)
    ] as "LEFT" | "RIGHT";
    const newBlock = { uid, startingPosition, side };
    // limit to 100 blocks to prevent the screen from freezing up
    setFailBlocks([newBlock, ...failBlocks].slice(0, 10));
  };


  return (
    <main className="flex h-screen flex-col items-center justify-between">
      <div className="flex w-full overflow-clip justify-center text-7xl font-mono">
        <div
          className="flex flex-row transition-all duration-1000 justify-end px-2 text-[#1a212c]"
          style={{
            height: "80px",
            width: `${Math.max(playerOneScore, 50)}rem`,
            backgroundColor: colors.player1,
          }}
        >
          <h3 className={`text-7xl font-mono ${jersey15.className}`}>
            {playerOneScore.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
          </h3>
        </div>
        <div
          className="flex flex-row transition-all duration-1000 justify-start px-2 text-white"
          style={{
            height: "80px",
            width: `${Math.max(playerTwoScore, 50)}rem`,
            backgroundColor: colors.player2,
          }}
        >
          <h3 className={`text-7xl font-mono ${jersey15.className}`}>
            {playerTwoScore.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
          </h3>
        </div>
      </div>

      <Canvas style={{ background: "white" }}>
        <ambientLight intensity={Math.PI / 2} />
        <pointLight position={[-10, -10, -10]} decay={0} intensity={2} />
        <pointLight position={[5, 5, 5]} decay={0} intensity={3} />
  
        <Player1 showResults={false} />
        <Player2 showResults={showResults} funnelX={player2FunnelX} />
  
        <GpuGroup
          positions={player1GpuPositions}
          stats={vmStats.statusArray.slice(0, 4)}
        />
  
        {/* Right side GPUs */}
        <GpuGroupRight
          positions={player2GpuPositions}
          stats={vmStats.statusArray.slice(4, 8)}
        />
      </Canvas>
  
      <CountdownOverlay
        timeElapsed={timeElapsed}
        timeRemaining={timeRemaining}
        playerOneScore={playerOneScore}
        playerTwoScore={playerTwoScore}
      />
  
      <ResultsOverlay
        showResults={showResults}
        playerOneScore={playerOneScore}
        playerTwoScore={playerTwoScore}
        playerName={playerName}
      />
    </main>
  );
}