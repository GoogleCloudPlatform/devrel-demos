'use client'

// // Uncomment the next two lines and start a game to create a new player list
// import { generatePlayerNameFile } from "./player-name-file-generator";
// generatePlayerNameFile();

import { playerNameList } from "@/utils/player-name-list";

export const generatePlayerName = () => {
  const currentMillisecond = new Date().getTime();
  // change the name every 58 seconds
  // this provides a full week of unique names
  const tenSecondIncrement = Math.floor(currentMillisecond / 58000);
  const indexToSelect = tenSecondIncrement % playerNameList.length;
  return playerNameList[indexToSelect];
}