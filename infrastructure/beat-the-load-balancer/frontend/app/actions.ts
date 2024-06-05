'use server'

import { main_vm_address } from '@/lbb.config'

const QUEUE_CAPACITY = 100;

const getRequest = async (url: string) => {
  try {
    const response = await fetch(url);
    const parsedResponse = await response.json();
    return parsedResponse;
  } catch (error) {
    console.error(`Failure making request to ${url}`)
    console.error(error);
    throw error;
  }
}

function checkSecretPassword(secretPassword: string) {
  if (process.env.SECRET_PASSWORD && secretPassword !== process.env.SECRET_PASSWORD) {
    throw new Error('Incorrect secret password');
  }
}

export async function checkSecretPasswordExists() {
  return !!process.env.SECRET_PASSWORD;
}

export async function setVm(vmSelected: { vmId: number }, secretPassword: string) {
  checkSecretPassword(secretPassword);
  return getRequest(`${main_vm_address}/vm/select/vm-wh0${vmSelected.vmId}`);
}

export async function stopGame(secretPassword: string) {
  checkSecretPassword(secretPassword);
  return getRequest(`${main_vm_address}/game/stop`);
}

export async function resetGame(secretPassword: string) {
  checkSecretPassword(secretPassword);
  await stopGame(secretPassword);
  return getRequest(`${main_vm_address}/game/reset`);
}

export async function startLoader(secretPassword: string) {
  checkSecretPassword(secretPassword);
  return getRequest(`${main_vm_address}/game/start`);
}

export async function getRawStats(secretPassword: string) {
  checkSecretPassword(secretPassword);
  return getRequest(`${main_vm_address}/vm/all/stats`);
}

export async function getVmAllStats(secretPassword: string) {
  checkSecretPassword(secretPassword);
  const parsedResponse = await getRawStats(secretPassword);
  const emptyObjectArray = [{}, {}, {}, {}, {}, {}, {}, {}];
  const statusArray = emptyObjectArray.map((status, index) => {
    const utilization = Math.max(Math.min(parsedResponse.QUEUE[index] / QUEUE_CAPACITY, 1), 0);
    const atMaxCapacity = parsedResponse.QUEUE[index] >= QUEUE_CAPACITY;
    return {
      cpu: parsedResponse.ALL_CPU[index],
      memory: parsedResponse.ALL_MEM[index],
      score: parsedResponse.ALL_SCORES[index],
      tasksCompleted: parsedResponse.ALL_TASKS_COMPLETED[index],
      tasksRegistered: parsedResponse.ALL_TASKS_REGISTERED[index],
      hostName: parsedResponse.ALL_VMS[index],
      crashCount: parsedResponse.ALL_VMS_CRASHES_COUNT[index],
      queue: Math.max(parsedResponse.QUEUE[index], 0),
      utilization,
      atMaxCapacity,
    }
  });
  const gameVmSelection = parsedResponse.GAME_VM_SELECTION;
  const gameVmSelectionIndex = parsedResponse.ALL_VMS.findIndex((vmName: string) => vmName === gameVmSelection);
  const vmStats = {
    statusArray,
    playerName: parsedResponse.GAME_PLAYER_NAME,
    gameVmSelection,
    gameVmSelectionIndex,
    gameVmSelectionUpdates: parsedResponse.GAME_VM_SELECTION_UPDATES,
    playerOneScore: statusArray.slice(0, 4).reduce((agg, vmStatus) => (agg + Number(vmStatus.score)), 0),
    playerTwoScore: statusArray.slice(4).reduce((agg, vmStatus) => (agg + Number(vmStatus.score)), 0),
  };
  return vmStats;
}

