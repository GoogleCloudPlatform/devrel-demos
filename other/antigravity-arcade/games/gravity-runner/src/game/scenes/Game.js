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
        // Standard low res game layer
        this.gameLayer = this.add.container(0, 0);

        // Starry Background (Game Quality skill)
        const bg = this.add.tileSprite(160, 120, 640, 480, 'background');
        bg.setTint(0x111122);
        this.gameLayer.add(bg);

        // Stars/particles background for visual game-quality compliance
        this.stars = [];
        for (let i = 0; i < 40; i++) {
            const star = this.add.rectangle(Math.random() * 320, Math.random() * 240, 2, 2, 0xffffff);
            star.setAlpha(0.3 + Math.random() * 0.7);
            this.gameLayer.add(star);
            this.stars.push(star);
        }

        this.platforms = [];

        // Add initial solid floor and ceiling across the screen
        const initialFloor = this.add.rectangle(160, 230, 320, 20, 0x00ffff).setDepth(5);
        const initialCeiling = this.add.rectangle(160, 10, 320, 20, 0xff00ff).setDepth(5);
        this.gameLayer.add(initialFloor);
        this.gameLayer.add(initialCeiling);
        this.platforms.push({ rect: initialFloor, type: 'floor' });
        this.platforms.push({ rect: initialCeiling, type: 'ceiling' });

        // Initial sky jump-through platform
        const skyPlat = this.add.rectangle(240, 120, 80, 10, 0xffff00).setDepth(5);
        this.gameLayer.add(skyPlat);
        this.platforms.push({ rect: skyPlat, type: 'sky' });

        const spikeUpGraphics = this.add.graphics();
        spikeUpGraphics.fillStyle(0xff0000, 1);
        spikeUpGraphics.fillTriangle(8, 0, 0, 24, 16, 24);
        spikeUpGraphics.generateTexture('spikeUp', 16, 24);
        spikeUpGraphics.destroy();

        const spikeDownGraphics = this.add.graphics();
        spikeDownGraphics.fillStyle(0xff0000, 1);
        spikeDownGraphics.fillTriangle(0, 0, 16, 0, 8, 24);
        spikeDownGraphics.generateTexture('spikeDown', 16, 24);
        spikeDownGraphics.destroy();

        // Core Gameplay State
        this.score = 0;
        this.gravityDirection = 1; // 1 = Floor, -1 = Ceiling
        this.isDashing = false;
        this.dashCooldown = 0;
        this.speedMultiplier = 1;
        this.gameOver = false;
        this.vy = 0;
        this.vx = 0;
        this.jumpBufferCounter = 0;
        this.coyoteTimeCounter = 0;
        this.onPlatform = true;

        // Player Setup (Square robot/runner)
        this.player = this.add.rectangle(60, 200, 16, 16, 0xffff00).setDepth(10);
        this.gameLayer.add(this.player);

        // Obstacles array
        this.obstacles = [];
        this.spawnTimer = 0;

        // Setup HUD with wide margin and retro font
        this.createHUD();

        // Input mapping matching input-mechanism skill
        this.cursors = this.input.keyboard.createCursorKeys();
        this.keys = this.input.keyboard.addKeys({
            w: Phaser.Input.Keyboard.KeyCodes.W,
            a: Phaser.Input.Keyboard.KeyCodes.A,
            s: Phaser.Input.Keyboard.KeyCodes.S,
            d: Phaser.Input.Keyboard.KeyCodes.D,
            z: Phaser.Input.Keyboard.KeyCodes.Z, // Button A
            x: Phaser.Input.Keyboard.KeyCodes.X, // Button B
            h: Phaser.Input.Keyboard.KeyCodes.H,
            r: Phaser.Input.Keyboard.KeyCodes.R
        });

        // Apply retro CRT Shader postFX wrapper
        this.cameras.main.setPostPipeline('CRTPipeline');

        // Layering Cameras and Scanlines setup
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

        // Control tutorial and start gate
        this.inputBuffer = [];
        this.cheatActive = false;
        this.gameStarted = false;

        this.tutorialContainer = this.add.container(640, 500).setDepth(120);
        const tutBg = this.add.rectangle(0, 0, 700, 200, 0x000000, 0.85);
        tutBg.setStrokeStyle(4, 0x00ffff);

        const tutTitle = this.add.text(0, -60, 'CONTROLS TUTORIAL', {
            fontFamily: '"Press Start 2P"', fontSize: 36, color: '#ffff00'
        }).setOrigin(0.5);

        const tutKeyboard = this.add.text(-180, 10, 'KEYBOARD\n[Z] : Jump\n[X] : Flip Gravity', {
            fontFamily: '"Press Start 2P"', fontSize: 15, color: '#ffffff', align: 'center'
        }).setOrigin(0.5);

        const tutGamepad = this.add.text(180, 10, 'GAMEPAD\n[A] : Jump\n[B] : Flip Gravity', {
            fontFamily: '"Press Start 2P"', fontSize: 15, color: '#00ffff', align: 'center'
        }).setOrigin(0.5);

        this.tutorialContainer.add([tutBg, tutTitle, tutKeyboard, tutGamepad]);
        this.cameras.main.ignore(this.tutorialContainer);

        this.initGamePad();
    }

    createHUD() {
        this.uiContainer = this.add.container(0, 0);

        // Extra UI margin adhering to game-quality rule
        this.scoreText = this.add.text(40, 40, 'DISTANCE: 0m', {
            fontFamily: '"Press Start 2P"', fontSize: 24, color: '#00ffff',
            stroke: '#000000', strokeThickness: 4
        }).setDepth(110);

        this.instructionText = this.add.text(40, 80, 'Z: Jump | X: Flip G', {
            fontFamily: '"Press Start 2P"', fontSize: 24, color: '#ffffff',
            stroke: '#000000', strokeThickness: 3
        }).setDepth(110);

        this.announcer = this.add.text(640, 400, '', {
            fontFamily: '"Press Start 2P"', fontSize: 48, color: '#ff0000',
            stroke: '#000000', strokeThickness: 8, align: 'center'
        }).setOrigin(0.5).setDepth(110);

        this.uiContainer.add([this.scoreText, this.instructionText, this.announcer]);
        this.cameras.main.ignore(this.uiContainer);
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
            isButtonJustDown: (index) => {
                const mappedIndex = index === 0 ? 1 : (index === 1 ? 0 : (index === 2 ? 3 : (index === 3 ? 2 : index)));
                const isDown = rawPad.isButtonDown(mappedIndex);
                if (!this.prevPadButtons) {
                    this.prevPadButtons = {};
                }
                const wasDown = this.prevPadButtons[mappedIndex] || false;
                this.prevPadButtons[mappedIndex] = isDown;
                return isDown && !wasDown;
            },
            left: rawPad.left,
            right: rawPad.right,
            up: rawPad.up,
            down: rawPad.down,
            axes: rawPad.axes,
            buttons: rawPad.buttons
        } : null;

        // Cache JustDown states for the entire frame so they are not consumed twice
        const justDownUp = Phaser.Input.Keyboard.JustDown(this.cursors.up);
        const justDownDown = Phaser.Input.Keyboard.JustDown(this.cursors.down);
        const justDownLeft = Phaser.Input.Keyboard.JustDown(this.cursors.left);
        const justDownRight = Phaser.Input.Keyboard.JustDown(this.cursors.right);
        const justDownX = Phaser.Input.Keyboard.JustDown(this.keys.x);
        const justDownZ = Phaser.Input.Keyboard.JustDown(this.keys.z);

        // Cheat code tracker
        const keysList = [
            { pressed: justDownUp, val: 'UP' },
            { pressed: justDownDown, val: 'DOWN' },
            { pressed: justDownLeft, val: 'LEFT' },
            { pressed: justDownRight, val: 'RIGHT' },
            { pressed: justDownX, val: 'X' },
            { pressed: justDownZ, val: 'Z' }
        ];

        for (const k of keysList) {
            if (k.pressed) {
                this.inputBuffer.push(k.val);
                if (this.inputBuffer.length > 10) this.inputBuffer.shift();

                const target = ['UP', 'UP', 'DOWN', 'DOWN', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'X', 'Z'];
                if (this.inputBuffer.join(',') === target.join(',')) {
                    if (!this.cheatActive) {
                        this.cheatActive = true;
                        const rand = Math.floor(Math.random() * 4);
                        if (rand === 0) this.cameras.main.postFX.addColorMatrix().grayscale();
                        else if (rand === 1) this.cameras.main.postFX.addColorMatrix().sepia();
                        else if (rand === 2) this.cameras.main.postFX.addColorMatrix().negative();
                        else this.cameras.main.postFX.addColorMatrix().night();

                        this.time.delayedCall(10000, () => {
                            this.cameras.main.postFX.clear();
                            this.cameras.main.setPostPipeline('CRTPipeline');
                            this.cheatActive = false;
                        });
                    }
                }
            }
        }

        if (!this.gameStarted) {
            const kbInput = this.cursors.left.isDown || this.cursors.right.isDown || this.cursors.up.isDown || this.cursors.down.isDown || this.keys.z.isDown || this.keys.x.isDown;
            const padInput = pad && (pad.buttons.some(b => b.pressed) || pad.axes.some(a => Math.abs(a.value) > 0.5));
            if (kbInput || padInput) {
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

        // System resets
        if (Phaser.Input.Keyboard.JustDown(this.keys.h) || (pad && pad.isButtonDown(8))) {
            window.parent.postMessage({ action: "GO_HOME" }, '*');
        }
        if (Phaser.Input.Keyboard.JustDown(this.keys.r) || (pad && pad.isButtonDown(9))) {
            window.parent.postMessage({ action: 'RELOAD_GAME' }, '*');
        }

        if (this.gameOver) return;

        // Endless Runner background scrolling
        for (const star of this.stars) {
            star.x -= (20 + this.speedMultiplier * 40) * delta / 1000;
            if (star.x < 0) {
                star.x = 320;
                star.y = Math.random() * 240;
            }
        }

        // Distance / Score progression
        this.score += delta * 0.05 * this.speedMultiplier;
        this.scoreText.setText(`DISTANCE: ${Math.floor(this.score)}m`);

        // Controller / Keyboard Inputs (Input-mechanism mapping)
        const moveLeft = this.keys.a.isDown || this.cursors.left.isDown || (pad && (pad.left || pad.axes[0]?.value < -0.5));
        const moveRight = this.keys.d.isDown || this.cursors.right.isDown || (pad && (pad.right || pad.axes[0]?.value > 0.5));
        const btnA = justDownX || (pad && pad.isButtonDown(0)); // Button A (Jump)
        const btnB = justDownZ || (pad && pad.isButtonJustDown(1)); // Button B (Flip Gravity)

        // Polished platformer: Decrease jump buffer and coyote time counters
        this.jumpBufferCounter -= delta;
        this.coyoteTimeCounter -= delta;

        // Check if grounded (screen edges or on a platform)
        const isGrounded = (this.gravityDirection === 1 && (this.player.y >= 210 || this.onPlatform)) ||
            (this.gravityDirection === -1 && (this.player.y <= 30 || this.onPlatform));

        if (isGrounded) {
            this.coyoteTimeCounter = 150; // Coyote time grace period (150ms)
        }

        // Jump input buffer
        if (btnA) {
            this.jumpBufferCounter = 150; // Buffer duration (150ms)
        }

        // Z: Regular platformer jump (Button A)
        if (this.jumpBufferCounter > 0 && (isGrounded || this.coyoteTimeCounter > 0)) {
            this.vy = this.gravityDirection === 1 ? -300 : 300;
            this.jumpBufferCounter = 0;
            this.coyoteTimeCounter = 0;
        }

        // Variable Jump Height: Reduce upward velocity if release early
        const jumpPressed = this.keys.x.isDown || this.cursors.up.isDown || (pad && pad.isButtonDown(0));
        if (!jumpPressed) {
            if (this.gravityDirection === 1 && this.vy < -100) {
                this.vy *= 0.85;
            } else if (this.gravityDirection === -1 && this.vy > 100) {
                this.vy *= 0.85;
            }
        }

        // X: Gravity Flip (Button B)
        if (btnB) {
            this.gravityDirection *= -1;
            this.cameras.main.shake(50, 0.005);
        }

        // Moving left/right with acceleration and friction
        const targetSpeed = moveLeft ? -120 : (moveRight ? 120 : 0);
        const accel = targetSpeed === 0 ? 600 : 800;

        if (this.vx < targetSpeed) {
            this.vx = Math.min(this.vx + accel * delta / 1000, targetSpeed);
        } else if (this.vx > targetSpeed) {
            this.vx = Math.max(this.vx - accel * delta / 1000, targetSpeed);
        }

        this.player.x += this.vx * delta / 1000;
        this.player.x = Phaser.Math.Clamp(this.player.x, 20, 300);

        // Apply vertical physics and gravity force
        this.player.y += this.vy * delta / 1000;
        if (this.gravityDirection === 1) {
            this.vy += 800 * delta / 1000;
        } else {
            this.vy -= 800 * delta / 1000;
        }

        this.onPlatform = false;
        for (const plat of this.platforms) {
            const px = plat.rect.x;
            const pw = plat.rect.width;
            const py = plat.rect.y;

            if (this.player.x >= px - pw / 2 && this.player.x <= px + pw / 2) {
                if (this.gravityDirection === 1 && this.vy > 0 && this.player.y >= py - 25 && this.player.y <= py + 10) {
                    this.player.y = py - 18;
                    this.vy = 0;
                    this.onPlatform = true;
                } else if (this.gravityDirection === -1 && this.vy < 0 && this.player.y <= py + 25 && this.player.y >= py - 10) {
                    this.player.y = py + 18;
                    this.vy = 0;
                    this.onPlatform = true;
                }
            }
        }

        // Scroll platforms left and spawn new ones (with pits)
        let maxFloorX = -Infinity;
        let maxCeilingX = -Infinity;

        for (let i = this.platforms.length - 1; i >= 0; i--) {
            const plat = this.platforms[i];
            plat.rect.x -= (150 + this.speedMultiplier * 20) * delta / 1000;

            if (plat.type === 'floor' && plat.rect.x + plat.rect.width / 2 > maxFloorX) {
                maxFloorX = plat.rect.x + plat.rect.width / 2;
            }
            if (plat.type === 'ceiling' && plat.rect.x + plat.rect.width / 2 > maxCeilingX) {
                maxCeilingX = plat.rect.x + plat.rect.width / 2;
            }

            if (plat.rect.x + plat.rect.width / 2 < 0) {
                plat.rect.destroy();
                this.platforms.splice(i, 1);
            }
        }

        // Generate new segments with occasional pits
        if (maxFloorX < 340) {
            const isPit = Math.random() < 0.25; // 25% chance for a pit gap
            const gap = isPit ? 80 : 0;
            const newFloor = this.add.rectangle(maxFloorX + 100 + gap, 230, 200, 20, 0x00ffff).setDepth(5);
            this.gameLayer.add(newFloor);
            this.platforms.push({ rect: newFloor, type: 'floor' });
        }

        if (maxCeilingX < 340) {
            const isPit = Math.random() < 0.25;
            const gap = isPit ? 80 : 0;
            const newCeiling = this.add.rectangle(maxCeilingX + 100 + gap, 10, 200, 20, 0xff00ff).setDepth(5);
            this.gameLayer.add(newCeiling);
            this.platforms.push({ rect: newCeiling, type: 'ceiling' });

            // Occasionally spawn sky jump-through platform
            if (Math.random() < 0.4) {
                const skyPlat = this.add.rectangle(maxCeilingX + 120, 120, 60, 10, 0xffff00).setDepth(5);
                this.gameLayer.add(skyPlat);
                this.platforms.push({ rect: skyPlat, type: 'sky' });
            }
        }

        // Check Pit Game Over
        if (this.player.y > 250 || this.player.y < -10) {
            this.gameOver = true;
            this.cameras.main.shake(250, 0.05);
            this.announcer.setText('FELL INTO PIT!\nRefresh to Try Again');
            window.parent.postMessage({ type: 'game-over', score: Math.floor(this.score) }, '*');
        }

        // Spawn Static Spikes safely (never above/below a pit)
        this.spawnTimer += delta;
        if (this.spawnTimer > 1200) {
            this.spawnTimer = 0;

            // Check if there is a solid platform at x=330
            let hasFloor = false;
            let hasCeiling = false;
            for (const plat of this.platforms) {
                const px = plat.rect.x;
                const pw = plat.rect.width;
                if (330 >= px - pw / 2 && 330 <= px + pw / 2) {
                    if (plat.type === 'floor') hasFloor = true;
                    if (plat.type === 'ceiling') hasCeiling = true;
                }
            }

            if (hasFloor || hasCeiling) {
                const spawnOnCeiling = hasCeiling && (!hasFloor || Math.random() > 0.5);
                if (spawnOnCeiling) {
                    const obs = this.add.sprite(330, 30, 'spikeDown').setDepth(8);
                    this.gameLayer.add(obs);
                    this.obstacles.push(obs);
                } else {
                    const obs = this.add.sprite(330, 210, 'spikeUp').setDepth(8);
                    this.gameLayer.add(obs);
                    this.obstacles.push(obs);
                }
            }
        }

        // Move Obstacles and detect collisions
        for (let i = this.obstacles.length - 1; i >= 0; i--) {
            const obs = this.obstacles[i];
            obs.x -= (150 + this.speedMultiplier * 20) * delta / 1000;

            if (obs.x < -20) {
                obs.destroy();
                this.obstacles.splice(i, 1);
                continue;
            }

            // Collisions (unless dashing which makes you temporarily invulnerable)
            if (!this.isDashing && Phaser.Math.Distance.Between(this.player.x, this.player.y, obs.x, obs.y) < 12) {
                this.gameOver = true;
                this.cameras.main.shake(250, 0.05); // Heavy death shake
                this.announcer.setText('GAME OVER\nRefresh to Try Again');

                // Send standard message to parent page based on iframe-connection skill
                window.parent.postMessage({
                    type: 'game-over',
                    score: Math.floor(this.score)
                }, '*');
            }
        }

        // Render frame
        this.gameBuffer.clear();
        this.gameBuffer.draw(this.gameLayer);
    }
}
