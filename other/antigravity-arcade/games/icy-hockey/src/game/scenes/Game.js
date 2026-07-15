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
        this.load.image('logo', 'logo.png');
    }

    create() {
        // Create low-res game layer
        this.gameLayer = this.add.container(0, 0);

        // 1. Ice Rink Aesthetics (320x240 game world)
        // Ice surface background
        const iceBg = this.add.rectangle(160, 120, 320, 240, 0xddf3f8);
        this.gameLayer.add(iceBg);

        // Rink Line Art
        this.rinkGraphics = this.add.graphics();

        // Blue Center Line
        this.rinkGraphics.lineStyle(2, 0x1976d2, 0.4);
        this.rinkGraphics.lineBetween(160, 0, 160, 240);

        // Blue Center Faceoff Circle
        this.rinkGraphics.strokeCircle(160, 120, 40);

        // Red Goal Lines
        this.rinkGraphics.lineStyle(2, 0xe53935, 0.4);
        this.rinkGraphics.lineBetween(20, 0, 20, 240);
        this.rinkGraphics.lineBetween(300, 0, 300, 240);

        this.gameLayer.add(this.rinkGraphics);

        // 2. Paddles & Puck Setup
        // Player paddle (Left Team)
        this.playerPaddle = this.add.rectangle(30, 120, 8, 40, 0x00b0ff).setDepth(10);
        this.gameLayer.add(this.playerPaddle);

        // Opponent paddle (Right Team)
        this.opponentPaddle = this.add.rectangle(290, 120, 8, 40, 0xff1744).setDepth(10);
        this.gameLayer.add(this.opponentPaddle);

        // Puck Setup
        this.puck = this.add.rectangle(160, 120, 8, 8, 0x263238).setDepth(10);
        this.gameLayer.add(this.puck);

        // Physics State
        this.puckSpeed = 140;
        this.puckVelocity = { x: -this.puckSpeed, y: 80 };

        // Core Gameplay State
        this.scoreLeft = 0;
        this.scoreRight = 0;
        this.gameOver = false;
        this.gameStarted = false;

        // HUD text objects on UI Camera
        this.createHUD();

        // Setup standard inputs
        this.cursors = this.input.keyboard.createCursorKeys();
        this.keys = this.input.keyboard.addKeys({
            w: Phaser.Input.Keyboard.KeyCodes.W,
            a: Phaser.Input.Keyboard.KeyCodes.A,
            s: Phaser.Input.Keyboard.KeyCodes.S,
            d: Phaser.Input.Keyboard.KeyCodes.D,
            z: Phaser.Input.Keyboard.KeyCodes.Z,
            x: Phaser.Input.Keyboard.KeyCodes.X,
            v: Phaser.Input.Keyboard.KeyCodes.V,
            h: Phaser.Input.Keyboard.KeyCodes.H,
            r: Phaser.Input.Keyboard.KeyCodes.R
        });

        // Input buffer for the konami cheat code
        this.inputBuffer = [];
        this.cheatActive = false;
        this.gameMode = '1player';

        // Tutorial overlay
        this.tutorialContainer = this.add.container(640, 480).setDepth(120);
        const tutBg = this.add.rectangle(0, 0, 800, 320, 0x000000, 0.85);
        tutBg.setStrokeStyle(4, 0x00ffff);

        const tutTitle = this.add.text(0, -100, 'ICY HOCKEY PONG', {
            fontFamily: '"Press Start 2P"', fontSize: 42, color: '#ffff00'
        }).setOrigin(0.5);

        const tutKeyboard = this.add.text(-200, -10, 'KEYBOARD\nP1: [W]/[S] or [↑]/[↓] : Move\nP2: [V] : Up | [X] : Down', {
            fontFamily: '"Press Start 2P"', fontSize: 12, color: '#ffffff', align: 'center'
        }).setOrigin(0.5);

        const tutGamepad = this.add.text(200, -10, 'GAMEPAD\nP1: D-PAD Up/Down : Move\nP2: [X] : Up | [A] : Down', {
            fontFamily: '"Press Start 2P"', fontSize: 12, color: '#00ffff', align: 'center'
        }).setOrigin(0.5);

        this.menuText1P = this.add.text(0, 70, '[X] / Button A : 1 PLAYER MODE', {
            fontFamily: '"Press Start 2P"', fontSize: 14, color: '#00ffff'
        }).setOrigin(0.5);

        this.menuText2P = this.add.text(0, 110, '[Z] / Button B : 2 PLAYER MODE', {
            fontFamily: '"Press Start 2P"', fontSize: 14, color: '#ffff00'
        }).setOrigin(0.5);

        this.tutorialContainer.add([tutBg, tutTitle, tutKeyboard, tutGamepad, this.menuText1P, this.menuText2P]);

        // Setup Cameras & post pipeline
        this.cameras.main.setPostPipeline('CRTPipeline');

        this.uiCamera = this.cameras.add(0, 0, this.scale.width, this.scale.height);

        this.gameBuffer = this.add.renderTexture(0, 0, 320, 240);
        this.gameBuffer.setOrigin(0, 0).setScale(4).setDepth(-1);

        this.cameras.main.ignore(this.gameLayer);
        this.uiCamera.ignore([this.gameLayer, this.gameBuffer]);

        const scanlineGraphics = this.add.graphics();
        scanlineGraphics.fillStyle(0x000000, 0.35);
        scanlineGraphics.fillRect(0, 3, 1, 1);
        scanlineGraphics.generateTexture('scanlines', 1, 4);
        scanlineGraphics.destroy();

        this.scanlines = this.add.tileSprite(0, 0, this.scale.width, this.scale.height, 'scanlines').setOrigin(0, 0);
        this.scanlines.setDepth(100);
        this.cameras.main.ignore(this.scanlines);

        this.initGamePad();
    }

    initGamePad() {
        this.input.gamepad.start();
        this.activeGamepad = null;

        // 2. Check for gamepads ALREADY connected before the game booted
        if (this.input.gamepad.total > 0) {
            // Grab the first available valid gamepad from Phaser's manager
            this.activeGamepad = this.input.gamepad.gamepads.find(pad => pad !== null);
            if (this.activeGamepad) {
                console.log(`Found pre-connected gamepad: ${this.activeGamepad.id}`);
            }
        }

        // 3. Fallback listener for gamepads plugged in AFTER the game started
        this.input.gamepad.on('connected', (pad) => {
            // Only assign it if we don't already have an active gamepad
            if (!this.activeGamepad) {
                this.activeGamepad = pad;
                console.log(`Gamepad plugged in mid-game: ${pad.id}`);
            }
        });
    }

    createHUD() {
        this.uiContainer = this.add.container(0, 0);

        // Score displays for Home & Away teams
        this.scoreTextLeft = this.add.text(60, 50, 'HOME: 0', {
            fontFamily: '"Press Start 2P"', fontSize: 28, color: '#00b0ff',
            stroke: '#000000', strokeThickness: 5
        }).setDepth(100);

        this.scoreTextRight = this.add.text(1020, 50, 'AWAY: 0', {
            fontFamily: '"Press Start 2P"', fontSize: 28, color: '#ff1744',
            stroke: '#000000', strokeThickness: 5
        }).setDepth(100);

        this.announcer = this.add.text(640, 400, '', {
            fontFamily: '"Press Start 2P"', fontSize: 48, color: '#ffd700',
            stroke: '#000000', strokeThickness: 8, align: 'center'
        }).setOrigin(0.5).setDepth(110);

        this.uiContainer.add([this.scoreTextLeft, this.scoreTextRight, this.announcer]);
        this.cameras.main.ignore(this.uiContainer);
    }

    announce(msg, duration = 2000) {
        this.announcer.setText(msg);
        this.time.delayedCall(duration, () => {
            this.announcer.setText('');
        });
    }

    resetPuck(scoringTeam) {
        this.puck.setPosition(160, 120);
        this.puckSpeed = 140;
        this.puckVelocity.x = scoringTeam === 'left' ? this.puckSpeed : -this.puckSpeed;
        this.puckVelocity.y = (Math.random() * 2 - 1) * 100;
    }

    update(time, delta) {
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

        const justDownUp = Phaser.Input.Keyboard.JustDown(this.cursors.up);
        const justDownDown = Phaser.Input.Keyboard.JustDown(this.cursors.down);
        const justDownLeft = Phaser.Input.Keyboard.JustDown(this.cursors.left);
        const justDownRight = Phaser.Input.Keyboard.JustDown(this.cursors.right);
        const justDownZ = Phaser.Input.Keyboard.JustDown(this.keys.z);
        const justDownX = Phaser.Input.Keyboard.JustDown(this.keys.x);

        // Home and Restart keys
        if (Phaser.Input.Keyboard.JustDown(this.keys.h) || (pad && pad.isButtonDown(8))) {
            window.parent.postMessage({ action: "GO_HOME" }, '*');
        }
        if (Phaser.Input.Keyboard.JustDown(this.keys.r) || (pad && pad.isButtonDown(9))) {
            window.parent.postMessage({ action: 'RELOAD_GAME' }, '*');
        }

        // Cheat code check
        const keys = [
            { pressed: justDownUp, val: 'UP' },
            { pressed: justDownDown, val: 'DOWN' },
            { pressed: justDownLeft, val: 'LEFT' },
            { pressed: justDownRight, val: 'RIGHT' },
            { pressed: justDownX, val: 'X' },
            { pressed: justDownZ, val: 'Z' }
        ];

        for (const k of keys) {
            if (k.pressed) {
                this.inputBuffer.push(k.val);
                if (this.inputBuffer.length > 10) this.inputBuffer.shift();

                const target = ['UP', 'UP', 'DOWN', 'DOWN', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'X', 'Z'];
                if (this.inputBuffer.join(',') === target.join(',')) {
                    if (!this.cheatActive) {
                        this.cheatActive = true;
                        this.announce("CHEAT ACTIVATED!\nSupersize Paddle!", 3000);
                        this.playerPaddle.setScale(1, 1.8);

                        const rand = Math.floor(Math.random() * 4);
                        if (rand === 0) this.cameras.main.postFX.addColorMatrix().grayscale();
                        else if (rand === 1) this.cameras.main.postFX.addColorMatrix().sepia();
                        else if (rand === 2) this.cameras.main.postFX.addColorMatrix().negative();
                        else this.cameras.main.postFX.addColorMatrix().night();

                        this.time.delayedCall(10000, () => {
                            this.cameras.main.postFX.clear();
                            this.cameras.main.setPostPipeline('CRTPipeline');
                            this.playerPaddle.setScale(1, 1);
                            this.cheatActive = false;
                        });
                    }
                }
            }
        }

        if (this.gameOver) return;

        if (!this.gameStarted) {
            const is1P = justDownX || (pad && pad.isButtonDown(0)); // Physical Button A
            const is2P = justDownZ || (pad && pad.isButtonDown(1)); // Physical Button B

            if (is1P || is2P) {
                this.gameMode = is1P ? '1player' : '2player';
                this.gameStarted = true;
                this.tweens.add({
                    targets: this.tutorialContainer,
                    alpha: 0,
                    duration: 1000,
                    onComplete: () => {
                        if (this.tutorialContainer) this.tutorialContainer.destroy();
                    }
                });
            } else {
                return;
            }
        }

        // 1. Paddle movement
        const speed = 160;

        if (this.gameMode === '1player') {
            let moveY = 0;
            if (this.cursors.up.isDown || this.keys.w.isDown || (pad && (pad.up || pad.axes[1].value < -0.5))) {
                moveY = -1;
            } else if (this.cursors.down.isDown || this.keys.s.isDown || (pad && (pad.down || pad.axes[1].value > 0.5))) {
                moveY = 1;
            }
            this.playerPaddle.y += moveY * (speed * delta / 1000);
            this.playerPaddle.y = Phaser.Math.Clamp(this.playerPaddle.y, 25, 215);

            // AI Chasing
            const aiSpeed = 110;
            if (this.puck.y < this.opponentPaddle.y - 8) {
                this.opponentPaddle.y -= aiSpeed * delta / 1000;
            } else if (this.puck.y > this.opponentPaddle.y + 8) {
                this.opponentPaddle.y += aiSpeed * delta / 1000;
            }
            this.opponentPaddle.y = Phaser.Math.Clamp(this.opponentPaddle.y, 25, 215);
        } else {
            // 2-Player Mode
            // Left Paddle: controlled with the keyboard arrow keys (or gamepad d-pad)
            let moveLeftY = 0;
            if (this.cursors.up.isDown || this.keys.w.isDown || (pad && (pad.up || pad.axes[1].value < -0.5))) {
                moveLeftY = -1;
            } else if (this.cursors.down.isDown || this.keys.s.isDown || (pad && (pad.down || pad.axes[1].value > 0.5))) {
                moveLeftY = 1;
            }
            this.playerPaddle.y += moveLeftY * (speed * delta / 1000);
            this.playerPaddle.y = Phaser.Math.Clamp(this.playerPaddle.y, 25, 215);

            // Right Paddle: controlled by Z and S keys (or gamepad face buttons: lower button and upper button)
            let moveRightY = 0;
            if (this.keys.x.isDown || (pad && pad.isButtonDown(0))) { // Physical Button A (sends key X / index 1)
                moveRightY = 1;
            } else if (this.keys.v.isDown || (pad && pad.isButtonDown(2))) { // Physical Button X (sends key V / index 3)
                moveRightY = -1;
            }
            this.opponentPaddle.y += moveRightY * (speed * delta / 1000);
            this.opponentPaddle.y = Phaser.Math.Clamp(this.opponentPaddle.y, 25, 215);
        }

        // 3. Puck Physics
        this.puck.x += this.puckVelocity.x * delta / 1000;
        this.puck.y += this.puckVelocity.y * delta / 1000;

        // Top and Bottom walls bounce
        if (this.puck.y <= 4) {
            this.puck.y = 4;
            this.puckVelocity.y *= -1;
        } else if (this.puck.y >= 236) {
            this.puck.y = 236;
            this.puckVelocity.y *= -1;
        }

        // Left paddle collision
        if (this.puckVelocity.x < 0 && this.puck.x <= 38 && this.puck.x >= 26) {
            if (this.puck.y >= this.playerPaddle.y - 22 && this.puck.y <= this.playerPaddle.y + 22) {
                this.puck.x = 38;
                this.puckSpeed = Math.min(300, this.puckSpeed + 15);
                const relY = (this.puck.y - this.playerPaddle.y) / 20;
                this.puckVelocity.x = this.puckSpeed;
                this.puckVelocity.y = relY * 120;
                this.cameras.main.shake(50, 0.003);
            }
        }

        // Right paddle collision
        if (this.puckVelocity.x > 0 && this.puck.x >= 282 && this.puck.x <= 294) {
            if (this.puck.y >= this.opponentPaddle.y - 22 && this.puck.y <= this.opponentPaddle.y + 22) {
                this.puck.x = 282;
                this.puckSpeed = Math.min(300, this.puckSpeed + 15);
                const relY = (this.puck.y - this.opponentPaddle.y) / 20;
                this.puckVelocity.x = -this.puckSpeed;
                this.puckVelocity.y = relY * 120;
                this.cameras.main.shake(50, 0.003);
            }
        }

        // 4. Scoring Points
        if (this.puck.x <= 10) {
            // Goal scored by Away team
            this.scoreRight += 1;
            this.scoreTextRight.setText(`AWAY: ${this.scoreRight}`);
            this.cameras.main.shake(200, 0.01);
            this.announce("GOAL FOR AWAY!", 1500);

            if (this.scoreRight >= 5) {
                this.announce("GAME OVER!\nAWAY TEAM WINS\nPress R to restart", 10000);
                this.gameOver = true;
                window.parent.postMessage({
                    type: 'game-over',
                    score: this.scoreLeft
                }, '*');
            } else {
                this.resetPuck('right');
            }
        } else if (this.puck.x >= 310) {
            // Goal scored by Home team
            this.scoreLeft += 1;
            this.scoreTextLeft.setText(`HOME: ${this.scoreLeft}`);
            this.cameras.main.shake(200, 0.01);
            this.announce("GOAL FOR HOME!", 1500);

            if (this.scoreLeft >= 5) {
                this.announce("VICTORY!\nHOME TEAM WINS\nPress R to restart", 10000);
                this.gameOver = true;
                window.parent.postMessage({
                    type: 'game-over',
                    score: this.scoreLeft
                }, '*');
            } else {
                this.resetPuck('left');
            }
        }

        // Redraw buffer
        this.gameBuffer.clear();
        this.gameBuffer.draw(this.gameLayer);
    }
}
