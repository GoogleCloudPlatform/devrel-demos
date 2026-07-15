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

import { Scene } from 'phaser';

export class Game extends Scene {
    constructor() {
        super('Game');
    }

    preload() {
        this.load.setPath('assets');

        // this.load.image('background', 'bg.png');
        this.load.image('logo', 'logo.png');
    }

    create() {
        // Create the low-res game layer (add your game sprites to this!)
        // This layer renders to a 320x240 buffer which is then upscaled 4x.
        this.gameLayer = this.add.container(0, 0);

        // Example background (placed in the 320x240 world)
        const bg = this.add.image(160, 120, 'background');
        this.gameLayer.add(bg);

        // Example UI objects (Drawn on UI camera at full 1280x960 resolution)
        this.add.image(640, 400, 'logo').setDepth(100);
        this.add.text(640, 600, 'Make something fun!\nand share it with us:\nsupport@phaser.io', {
            fontFamily: 'Arial Black', fontSize: 38, color: '#ffffff',
            stroke: '#000000', strokeThickness: 8,
            align: 'center'
        }).setOrigin(0.5).setDepth(100);

        // Setup standard inputs for Arcade compliance
        this.cursors = this.input.keyboard.createCursorKeys();
        this.keys = this.input.keyboard.addKeys({
            h: Phaser.Input.Keyboard.KeyCodes.H,
            r: Phaser.Input.Keyboard.KeyCodes.R
        });

        // Apply retro CRTPipeline shader to the main camera
        this.cameras.main.setPostPipeline('CRTPipeline');

        // Create a separate UI Camera that sits on top (keeps text crisp)
        this.uiCamera = this.cameras.add(0, 0, this.scale.width, this.scale.height);

        // Create the low-res game buffer (320x240 upscaled 4x to fill 1280x960)
        this.gameBuffer = this.add.renderTexture(0, 0, 320, 240);
        this.gameBuffer.setOrigin(0, 0).setScale(4).setDepth(-1);

        // Setup camera ignores (Main camera only draws the upscaled buffer)
        this.cameras.main.ignore(this.gameLayer);
        this.uiCamera.ignore([this.gameLayer, this.gameBuffer]);

        // Create scanline overlay
        const scanlineGraphics = this.add.graphics();
        scanlineGraphics.fillStyle(0x000000, 0.35);
        scanlineGraphics.fillRect(0, 3, 1, 1);
        scanlineGraphics.generateTexture('scanlines', 1, 4);
        scanlineGraphics.destroy();

        this.scanlines = this.add.tileSprite(0, 0, this.scale.width, this.scale.height, 'scanlines').setOrigin(0, 0);
        this.scanlines.setDepth(100);
        this.cameras.main.ignore(this.scanlines); // UI camera will render scanlines

        this.initGamePad();
    }

    initGamePad() {
        this.input.gamepad.start();
        this.activeGamepad = null;

        // 1. Check for gamepads ALREADY connected before the game booted
        if (this.input.gamepad.total > 0) {
            // Grab the first available valid gamepad from Phaser's manager
            this.activeGamepad = this.input.gamepad.gamepads.find(pad => pad !== null);
            if (this.activeGamepad) {
                console.log(`Found pre-connected gamepad: ${this.activeGamepad.id}`);
            }
        }

        // 2. Fallback listener for gamepads plugged in AFTER the game started
        this.input.gamepad.on('connected', (pad) => {
            // Only assign it if we don't already have an active gamepad
            if (!this.activeGamepad) {
                this.activeGamepad = pad;
                console.log(`Gamepad plugged in mid-game: ${pad.id}`);
            }
        });
    }

    update() {
        const rawPad = this.activeGamepad;

        // Remap hardware wiring inversion where physical face buttons are swapped:
        // Physical wiring: B=0, A=1, Y=2, X=3, Home=8, Restart=9
        // Standard Web Gamepad API: A=0, B=1, X=2, Y=3
        const pad = rawPad ? {
            ...rawPad,
            A: rawPad.B,
            B: rawPad.A,
            X: rawPad.Y,
            Y: rawPad.X,
            isButtonDown: (index) => {
                if (index === 0) return rawPad.isButtonDown(1);
                if (index === 1) return rawPad.isButtonDown(0);
                if (index === 2) return rawPad.isButtonDown(3);
                if (index === 3) return rawPad.isButtonDown(2);
                return rawPad.isButtonDown(index);
            },
            left: rawPad.left,
            right: rawPad.right,
            up: rawPad.up,
            down: rawPad.down,
            axes: rawPad.axes,
            buttons: rawPad.buttons
        } : null;

        // Home action (Keyboard 'H' or Gamepad Button 8)
        if (Phaser.Input.Keyboard.JustDown(this.keys.h) || (pad && pad.isButtonDown(8))) {
            window.parent.postMessage({ action: "GO_HOME" }, '*');
        }

        // Reload action (Keyboard 'R' or Gamepad Button 9)
        if (Phaser.Input.Keyboard.JustDown(this.keys.r) || (pad && pad.isButtonDown(9))) {
            window.parent.postMessage({ action: 'RELOAD_GAME' }, '*');
        }

        // Standard movement booleans (Available for the game logic)
        const moveLeft = this.cursors.left.isDown || (pad && (pad.left || pad.axes[0].value < -0.5));
        const moveRight = this.cursors.right.isDown || (pad && (pad.right || pad.axes[0].value > 0.5));
        const moveUp = this.cursors.up.isDown || (pad && (pad.up || pad.axes[1].value < -0.5));
        const moveDown = this.cursors.down.isDown || (pad && (pad.down || pad.axes[1].value > 0.5));

        // Draw low-res world to buffer (Keep at bottom of update)
        this.gameBuffer.clear();
        this.gameBuffer.draw(this.gameLayer);
    }
}
