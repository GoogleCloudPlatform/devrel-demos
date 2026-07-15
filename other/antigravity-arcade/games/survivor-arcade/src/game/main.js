// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { Game as MainGame } from './scenes/Game';
import { AUTO, Scale, Game } from 'phaser';
import { CRTPipeline } from './shaders/CRTShader';

// Find out more information about the Game Config at:
// https://docs.phaser.io/api-documentation/typedef/types-core#gameconfig
const config = {
    type: AUTO,

    width: 1280,
    height: 960,
    parent: 'game-container',
    backgroundColor: '#000000',
    pixelArt: true,
    preserveDrawingBuffer: true,
    physics: {
        default: 'arcade',
        arcade: {
            debug: false
        }
    },

    input: {
        gamepad: true
    },

    fps: {
        target: 60,
        forceSetTimeOut: true // Bypasses rAF to ensure speed doesn't change on high Hz monitors
    },

    scale: {
        mode: Scale.NONE,
        autoCenter: Scale.CENTER_BOTH
    },
    pipeline: { CRTPipeline },
    scene: [MainGame]
};

const StartGame = (parent) => {
    return new Game({ ...config, parent });
}

export default StartGame;
