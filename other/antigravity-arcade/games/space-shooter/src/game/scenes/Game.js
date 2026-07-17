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
    }

    create() {
        // Create scrolling starfield
        // Procedurally generate a 1px retro starfield texture to ensure exact sizing
        const starGraphics = this.add.graphics();

        // White stars
        starGraphics.fillStyle(0xffffff, 1);
        for (let i = 0; i < 40; i++) {
            starGraphics.fillRect(Phaser.Math.Between(0, 255), Phaser.Math.Between(0, 255), 1, 1);
        }
        // Cyan stars
        starGraphics.fillStyle(0x00ffff, 1);
        for (let i = 0; i < 20; i++) {
            starGraphics.fillRect(Phaser.Math.Between(0, 255), Phaser.Math.Between(0, 255), 1, 1);
        }
        // Magenta stars
        starGraphics.fillStyle(0xff00ff, 1);
        for (let i = 0; i < 20; i++) {
            starGraphics.fillRect(Phaser.Math.Between(0, 255), Phaser.Math.Between(0, 255), 1, 1);
        }
        // Yellow stars
        starGraphics.fillStyle(0xffff00, 1);
        for (let i = 0; i < 20; i++) {
            starGraphics.fillRect(Phaser.Math.Between(0, 255), Phaser.Math.Between(0, 255), 1, 1);
        }

        starGraphics.generateTexture('stars', 256, 256);
        starGraphics.destroy();

        this.stars = this.add.tileSprite(0, 0, 320, 240, 'stars').setOrigin(0, 0);

        // Initial speed
        this.starSpeed = 2;

        // Create player texture procedurally
        const playerGraphics = this.add.graphics();
        playerGraphics.fillStyle(0xffffff, 1); // White
        playerGraphics.fillTriangle(0, 15, 8, 0, 15, 15); // Smaller for 320x240
        playerGraphics.generateTexture('playerShip', 16, 16);
        playerGraphics.destroy();

        this.player = this.physics.add.sprite(160, 200, 'playerShip');
        this.player.setCollideWorldBounds(true);
        this.physics.world.setBounds(0, 0, 320, 240);

        this.cursors = this.input.keyboard.createCursorKeys();

        // Custom keys for arcade mapping
        this.keys = this.input.keyboard.addKeys({
            h: Phaser.Input.Keyboard.KeyCodes.H,
            r: Phaser.Input.Keyboard.KeyCodes.R,
            z: Phaser.Input.Keyboard.KeyCodes.Z,
            x: Phaser.Input.Keyboard.KeyCodes.X,
            c: Phaser.Input.Keyboard.KeyCodes.C,
            v: Phaser.Input.Keyboard.KeyCodes.V
        });

        // Apply retro CRTPipeline shader to the main camera
        this.cameras.main.setPostPipeline('CRTPipeline');

        this.gameLayer = this.add.container(0, 0);
        this.gameLayer.add([this.stars, this.player]);

        // Create bullet texture procedurally
        const bulletGraphics = this.add.graphics();
        bulletGraphics.fillStyle(0xffffff, 1);
        bulletGraphics.fillRect(0, 0, 2, 4);
        bulletGraphics.generateTexture('bullet', 2, 4);
        bulletGraphics.destroy();

        this.bullets = this.physics.add.group({
            defaultKey: 'bullet',
            maxSize: 30
        });

        this.nextFire = 0;
        this.fireRate = 100; // Faster for autofire feel

        this.score = 0;
        this.lives = 3;

        this.lastInputTime = 0;
        this.isAttractMode = false;
        this.gameOverTime = 0;

        const enemyGraphics = this.add.graphics();
        enemyGraphics.fillStyle(0x88ccff, 1); // Light Blue

        // Draw a 16x16 triangle inside an 18x18 canvas to pad against atlas bleed while maintaining original size
        enemyGraphics.fillTriangle(1, 1, 16, 1, 8.5, 16);

        enemyGraphics.generateTexture('enemyShip', 18, 18);
        enemyGraphics.destroy();

        this.enemies = this.physics.add.group();

        this.spawnTimer = 0;
        this.spawnInterval = 2000; // Start with 2s interval for Stage 1
        this.maxEnemies = 2; // Start with 2 enemies for Stage 1

        // Stage state
        this.currentStage = 1;
        this.stageDuration = 20000; // 20 seconds
        this.stageStartTime = 0; // Will be set on start
        this.stageElapsed = 0;

        this.scoreText = this.add.text(16, 16, 'Score: 0', { fontFamily: '"Press Start 2P"', fontSize: '24px', fill: '#fff' });
        this.livesText = this.add.text(16, 56, 'Lives: 3', { fontFamily: '"Press Start 2P"', fontSize: '24px', fill: '#fff' });

        this.stageText = this.add.text(640, 480, 'STAGE 1', { fontFamily: '"Press Start 2P"', fontSize: '48px', fill: '#fff' }).setOrigin(0.5);
        this.stageText.setDepth(100);
        this.stageText.setVisible(false); // Hidden by default, triggered by startStage

        this.gameOverText = this.add.text(640, 480, 'GAME OVER', { fontFamily: '"Press Start 2P"', fontSize: '64px', fill: '#ff0000' }).setOrigin(0.5);
        this.gameOverText.setDepth(100);
        this.gameOverText.setVisible(false);

        this.demoText = this.add.text(640, 300, 'DEMO MODE', { fontFamily: '"Press Start 2P"', fontSize: '48px', fill: '#ffff00' }).setOrigin(0.5);
        this.demoText.setDepth(100);
        this.demoText.setVisible(false);

        this.isGameOver = false;

        this.progressBar = this.add.graphics();
        this.progressBar.setDepth(100);

        // Collisions
        this.physics.add.overlap(this.bullets, this.enemies, this.hitEnemy, null, this);
        this.physics.add.overlap(this.player, this.enemies, this.hitPlayer, null, this);

        // We use Vignette to darken the screen edges, simulating the curved glass of an old CRT monitor.
        this.cameras.main.setPostPipeline('CRTPipeline');

        // Create a separate UI Camera that sits on top of the main camera.
        // This camera will NOT have the heavy postFX effects, keeping the text readable.
        this.uiCamera = this.cameras.add(0, 0, this.scale.width, this.scale.height);

        // Tell the main camera to ignore the UI text objects.
        // Create the low-res game buffer (256x192 is 1/4 of 1024x768)
        this.gameBuffer = this.add.renderTexture(0, 0, 320, 240);
        this.gameBuffer.setOrigin(0, 0); // Explicit origin
        this.gameBuffer.setScale(4); // Upscale 4x to fill 1280x960
        this.gameBuffer.setDepth(-1); // Ensure it renders behind UI

        // Setup cameras
        this.cameras.main.ignore([this.gameLayer, this.scoreText, this.livesText, this.stageText, this.gameOverText, this.demoText, this.progressBar]);
        this.uiCamera.ignore([this.gameLayer, this.gameBuffer]);

        // Create scanline overlay using a 1x2 pixel TileSprite
        const scanlineGraphics = this.add.graphics();
        scanlineGraphics.fillStyle(0x000000, 0.35); // Boosted scanline effect to run over bright enemies
        scanlineGraphics.fillRect(0, 3, 1, 1); // Row 4 is dark (1 in 4)
        scanlineGraphics.generateTexture('scanlines', 1, 4);
        scanlineGraphics.destroy();

        this.scanlines = this.add.tileSprite(0, 0, this.scale.width, this.scale.height, 'scanlines').setOrigin(0, 0);
        this.scanlines.setDepth(100); // Render above everything

        // Let the UI Camera render the scanlines (ignore in main camera to avoid double rendering)
        this.cameras.main.ignore(this.scanlines);

        // Input mechanism tutorial and cheat buffer
        this.inputBuffer = [];
        this.cheatActive = false;
        this.gameStarted = false;

        this.tutorialContainer = this.add.container(640, 500).setDepth(120);
        const tutBg = this.add.rectangle(0, 0, 700, 300, 0x000000, 0.85);
        tutBg.setStrokeStyle(4, 0x00ffff);

        const tutTitle = this.add.text(0, -110, 'CONTROLS TUTORIAL', {
            fontFamily: '"Press Start 2P"', fontSize: 36, color: '#ffff00'
        }).setOrigin(0.5);

        const tutKeyboard = this.add.text(-180, 0, 'KEYBOARD\n[↑][↓][←][→] : Move\n[Z] : Button 1 (Action)\n[X] : Button 2 (Cancel)', {
            fontFamily: '"Press Start 2P"', fontSize: 12, color: '#ffffff', align: 'center'
        }).setOrigin(0.5);

        const tutGamepad = this.add.text(180, 0, 'GAMEPAD\nD-PAD / L-STICK : Move\n[A] Face Button : Action\n[B] Face Button : Cancel', {
            fontFamily: '"Press Start 2P"', fontSize: 12, color: '#00ffff', align: 'center'
        }).setOrigin(0.5);

        this.tutorialContainer.add([tutBg, tutTitle, tutKeyboard, tutGamepad]);
        this.cameras.main.ignore(this.tutorialContainer);

        this.initGamePad();
        // Wait for input to start the first stage
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

        // Cheat code sequence tracker
        const keysList = [
            { key: this.cursors.up, val: 'UP' },
            { key: this.cursors.down, val: 'DOWN' },
            { key: this.cursors.left, val: 'LEFT' },
            { key: this.cursors.right, val: 'RIGHT' },
            { key: this.keys.x, val: 'X' },
            { key: this.keys.z, val: 'Z' }
        ];

        for (const k of keysList) {
            if (Phaser.Input.Keyboard.JustDown(k.key)) {
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
                this.startStage(1);
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

        // Check for any input to reset inactivity timer
        const kbInput = this.cursors.left.isDown || this.cursors.right.isDown || this.cursors.up.isDown || this.cursors.down.isDown || this.keys.z.isDown || this.keys.x.isDown;
        const padInput = pad && (pad.buttons.some(b => b.pressed) || pad.axes.some(a => Math.abs(a.value) > 0.5));
        const anyInput = kbInput || padInput;

        if (anyInput) {
            this.lastInputTime = this.time.now;
            if (this.isAttractMode) {
                this.isAttractMode = false;
                this.demoText.setVisible(false);
                this.resetGame();
                return;
            }
        }

        // Trigger attract mode after 10 seconds of inactivity
        if (!this.isAttractMode && this.time.now - this.lastInputTime > 10000) {
            this.isAttractMode = true;
            this.demoText.setVisible(true);
            this.resetGame();
            return;
        }

        if (this.isGameOver) {
            const fireButton = Phaser.Input.Keyboard.JustDown(this.keys.x) || (pad && pad.isButtonDown(0));

            // In attract mode, auto-restart after 5 seconds
            const shouldRestart = fireButton || (this.isAttractMode && (this.time.now - this.gameOverTime > 5000));

            if (shouldRestart) {
                this.resetGame();
            }
            return;
        }

        // Reset velocity
        this.player.setVelocity(0);

        // Home action (Keyboard 'H' or Gamepad Start/Back)
        // On many pads Button 9 is Start, Button 8 is Select.
        // User asked for Back=Home, Select=Restart.
        if (Phaser.Input.Keyboard.JustDown(this.keys.h) || (pad && pad.isButtonDown(8))) {
            window.parent.postMessage({ action: "GO_HOME" }, '*');
        }

        // Reload action (Keyboard 'R' or Gamepad Select)
        if (Phaser.Input.Keyboard.JustDown(this.keys.r) || (pad && pad.isButtonDown(9))) {
            window.parent.postMessage({ action: 'RELOAD_GAME' }, '*');
        }

        // Movement (Support arrows and Gamepad D-pad/Left stick)
        let moveLeft = this.cursors.left.isDown || (pad && (pad.left || pad.axes[0].value < -0.5));
        let moveRight = this.cursors.right.isDown || (pad && (pad.right || pad.axes[0].value > 0.5));
        let moveUp = this.cursors.up.isDown || (pad && (pad.up || pad.axes[1].value < -0.5));
        let moveDown = this.cursors.down.isDown || (pad && (pad.down || pad.axes[1].value > 0.5));

        if (this.isAttractMode) {
            let closestEnemy = null;
            let minDistance = Infinity;
            this.enemies.getChildren().forEach(enemy => {
                if (enemy.active && enemy.y > 100) { // Let enemies get closer
                    const distance = Phaser.Math.Distance.Between(this.player.x, this.player.y, enemy.x, enemy.y);
                    if (distance < minDistance) {
                        minDistance = distance;
                        closestEnemy = enemy;
                    }
                }
            });

            if (closestEnemy) {
                moveLeft = closestEnemy.x < this.player.x - 5;
                moveRight = closestEnemy.x > this.player.x + 5;
                moveUp = false;
                moveDown = false;
            } else {
                moveLeft = this.player.x > 165;
                moveRight = this.player.x < 155;
                moveUp = false;
                moveDown = false;
            }
        }

        if (moveLeft) {
            this.player.setVelocityX(-200); // Halved speed for better control
        } else if (moveRight) {
            this.player.setVelocityX(200); // Halved speed for better control
        }

        if (moveUp) {
            this.player.setVelocityY(-150); // Halved speed
            this.starSpeed = 6;
        } else if (moveDown) {
            this.player.setVelocityY(150); // Halved speed
            this.starSpeed = 1;
        } else {
            this.starSpeed = 3;
        }

        // Clamp player to bottom 1/3 of the screen
        this.player.y = Phaser.Math.Clamp(this.player.y, 160, 230);

        // Fire (Keyboard 'X' mapped to Physical Button A or Gamepad Button A)
        // pad.A maps to physical index 0.
        let fireButton = this.keys.x.isDown || (pad && pad.isButtonDown(0));

        if (this.isAttractMode) {
            // Burst fire logic
            const burstInterval = 1000; // 1 second cycle
            const burstDuration = 300; // Fire for 300ms
            const inBurst = (this.time.now % burstInterval) < burstDuration;

            // Only fire if there are enemies close enough (below y=100)
            const hasCloseEnemy = this.enemies.getChildren().some(enemy => enemy.active && enemy.y > 100);

            fireButton = hasCloseEnemy && inBurst;
        }

        if (fireButton && this.time.now > this.nextFire) {
            this.nextFire = this.time.now + this.fireRate;
            const bullet = this.bullets.get(this.player.x, this.player.y - 10);
            if (bullet) {
                bullet.setActive(true);
                bullet.setVisible(true);
                bullet.body.enable = true;
                bullet.body.reset(this.player.x, this.player.y - 10);
                bullet.body.velocity.y = -600;
                this.gameLayer.add(bullet); // Move to low-res layer
            }
        }

        // Recycle bullets
        this.bullets.children.each(bullet => {
            if (bullet.active && bullet.y < 0) {
                bullet.setActive(false);
                bullet.setVisible(false);
                bullet.body.enable = false;
            }
        });

        // Scroll starfield
        this.stars.tilePositionY -= this.starSpeed;

        // Update stage timer
        this.stageElapsed = this.time.now - this.stageStartTime;

        if (this.stageElapsed >= this.stageDuration) {
            if (this.currentStage < 10) {
                this.startStage(this.currentStage + 1);
            } else {
                this.triggerGameOver();
            }
        }

        // Draw progress bar (Thermometer UI space 1280x960)
        this.progressBar.clear();

        // Draw 10 stage ticks along the side
        this.progressBar.fillStyle(0x888888, 1);
        for (let i = 1; i <= 10; i++) {
            const tickY = 880 - (i * 80);
            this.progressBar.fillRect(1240, tickY, 10, 2); // Tick marks
        }

        // Draw Bulb at bottom
        this.progressBar.fillStyle(0x00ff00, 1);
        this.progressBar.lineStyle(2, 0x888888, 1);
        this.progressBar.strokeRect(1250, 80, 16, 800); // Outer box

        // Cumulative progress: Total time elapsed over all 10 stages
        const totalElapsed = ((this.currentStage - 1) * this.stageDuration) + Math.min(this.stageDuration, this.stageElapsed);
        const totalDuration = 10 * this.stageDuration; // 200s total for game
        const progressPercent = Math.min(1, totalElapsed / totalDuration);
        const fillHeight = progressPercent * 800; // Full height represents game completion

        this.progressBar.fillStyle(0x00ff00, 1); // Green line
        this.progressBar.fillRect(1252, 880 - fillHeight, 12, fillHeight); // Fills bottom to top

        if (this.time.now > this.spawnTimer) {
            this.spawnTimer = this.time.now + this.spawnInterval;
            this.spawnEnemy();
        }

        // Clean up off-screen enemies
        this.enemies.children.each(enemy => {
            if (enemy.active && enemy.y > 240) {
                enemy.destroy();
            }
        });

        // Draw low-res world to buffer
        this.gameBuffer.clear();
        this.gameBuffer.draw(this.gameLayer);
    }
    spawnEnemy() {
        if (this.enemies.countActive() >= this.maxEnemies) {
            return; // Cap active enemies
        }
        const x = Phaser.Math.Between(20, 300);
        const enemy = this.enemies.create(x, -20, 'enemyShip');
        if (enemy) {
            enemy.setVelocityY(50); // Slower movement keeps them on screen longer to fill the 20-pool
            this.gameLayer.add(enemy); // Add to low-res layer
        }
    }

    hitEnemy(bullet, enemy) {
        this.createExplosion(enemy.x, enemy.y, 0x88ccff); // Light blue explosion

        bullet.setActive(false);
        bullet.setVisible(false);
        bullet.body.enable = false;
        enemy.destroy();

        this.score += 10;
        this.scoreText.setText('Score: ' + this.score);
        console.log('Score: ' + this.score);
    }

    hitPlayer(player, enemy) {
        this.createExplosion(player.x, player.y, 0xffffff); // White explosion for player
        this.createExplosion(enemy.x, enemy.y, 0x88ccff); // Light blue explosion for enemy

        enemy.destroy();

        this.lives -= 1;
        this.livesText.setText('Lives: ' + this.lives);

        // Hide player and disable physics during the 2s "death" delay
        this.player.setActive(false).setVisible(false);
        if (this.player.body) this.player.body.enable = false;

        this.respawnTimer = this.time.delayedCall(2000, () => {
            if (this.lives <= 0) {
                this.triggerGameOver();
                return;
            }

            this.player.setPosition(160, 200);
            this.player.setActive(true).setVisible(true);
            if (this.player.body) this.player.body.enable = true;

            // Restart the current stage on death
            this.startStage(this.currentStage);

            // Flash the player to indicate hit/respawn
            this.tweens.add({
                targets: this.player,
                alpha: 0.2,
                duration: 100,
                yoyo: true,
                repeat: 5,
                onComplete: () => {
                    this.player.alpha = 1;
                }
            });
        });
    }

    triggerGameOver() {
        this.isGameOver = true;
        this.gameOverTime = this.time.now;
        this.gameOverText.setVisible(true);
        this.enemies.clear(true, true); // Stop enemies
        this.player.setActive(false).setVisible(false);
        if (this.player.body) this.player.body.enable = false;

        if (this.respawnTimer) {
            this.respawnTimer.remove();
        }
    }

    resetGame() {
        this.isGameOver = false;
        this.gameOverText.setVisible(false);
        this.score = 0;
        this.scoreText.setText('Score: ' + this.score);
        this.lives = 3;
        this.livesText.setText('Lives: ' + this.lives);
        this.player.setPosition(160, 200);
        this.player.setActive(true).setVisible(true);
        if (this.player.body) this.player.body.enable = true;
        this.startStage(1);
    }

    /**
     * Creates a particle explosion effect.
     * Uses the 'bullet' texture as shrapnel/debris.
     *
     * @param {number} x The x coordinate.
     * @param {number} y The y coordinate.
     * @param {number} color The tint color.
     */
    createExplosion(x, y, color) {
        // Layer 1: Fast, high-velocity shrapnel (Doubled size and speed)
        const emitter1 = this.add.particles(x, y, 'bullet', {
            speed: { min: 200, max: 600 },
            angle: { min: 0, max: 360 },
            scale: { start: 1.0, end: 0 },
            lifespan: 500,
            quantity: 6,
            stopAfter: 6,
            tint: color
        });
        this.gameLayer.add(emitter1);

        // Layer 2: Slow, larger debris expansion
        const emitter2 = this.add.particles(x, y, 'bullet', {
            speed: { min: 50, max: 200 },
            angle: { min: 0, max: 360 },
            scale: { start: 1.5, end: 0 },
            lifespan: 800,
            quantity: 4,
            stopAfter: 4,
            tint: color
        });
        this.gameLayer.add(emitter2);

        this.uiCamera.ignore([emitter1, emitter2]); // Keep it Press Start 2Pd

        this.time.delayedCall(1000, () => {
            emitter1.destroy();
            emitter2.destroy();
        });
    }

    /**
     * Starts a new stage, resets timers, clears enemies, and updates difficulty.
     *
     * @param {number} stage The stage number to start.
     */
    startStage(stage) {
        this.currentStage = stage;
        this.stageStartTime = this.time.now;
        this.stageElapsed = 0;

        // Clear enemies for a fresh start
        this.enemies.clear(true, true);

        // Update difficulty
        this.maxEnemies = stage * 2;
        this.spawnInterval = Math.max(250, 2000 - (stage - 1) * 200);

        // Show Stage text
        this.stageText.setText('STAGE ' + stage);
        this.stageText.setAlpha(1);
        this.stageText.setVisible(true);

        if (this.stageTween) this.stageTween.stop();

        this.stageTween = this.tweens.add({
            targets: this.stageText,
            alpha: 0,
            duration: 1000,
            delay: 1500,
            onComplete: () => {
                this.stageText.setVisible(false);
            }
        });
    }
}
