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
        // Create the low-res game layer (renders to 320x240 buffer)
        this.gameLayer = this.add.container(0, 0);

        // Add a tiled background to represent the dungeon/arena floor
        const bg = this.add.tileSprite(160, 120, 640, 480, 'background');
        bg.setTint(0x222244); // Dark mystical dungeon floor
        this.gameLayer.add(bg);

        // Generate custom retro/neon arcade pixel art textures using Graphics
        this.generateArcadeTextures();

        // Core Gameplay State
        this.playerStats = {
            maxHp: 100,
            currentHp: 100,
            level: 1,
            xp: 0,
            xpToNextLevel: 50,
            damage: 15,
            fireDelay: 600,
            speed: 80,
            score: 0
        };

        // Add the Player to the game layer
        this.player = this.add.sprite(160, 120, 'player').setDepth(10);
        this.gameLayer.add(this.player);

        // Draw retro ring around the player showing auto-attack range (70 units)
        this.rangeRing = this.add.graphics();
        this.rangeRing.lineStyle(1, 0x00ffff, 0.4);
        this.rangeRing.strokeCircle(0, 0, 70);
        this.rangeRing.x = 160;
        this.rangeRing.y = 120;
        this.rangeRing.setDepth(9);
        this.gameLayer.add(this.rangeRing);

        // Entities Groups
        this.enemies = [];
        this.projectiles = [];
        this.xpGems = [];

        // Timers for spawning and shooting
        this.lastShotTime = 0;
        this.lastSpawnTime = 0;
        this.spawnInterval = 2000; // Spawns every 2s initially

        // Setup UI / HUD Objects on UI Camera (1280x960)
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
            h: Phaser.Input.Keyboard.KeyCodes.H,
            r: Phaser.Input.Keyboard.KeyCodes.R
        });

        this.inputBuffer = [];
        this.cheatActive = false;

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

        // Start the wave banner
        this.announce("Survivor Arcade\nDefeat waves to collect XP!", 3000);

        // Control Explainer / Tutorial Diagram
        this.tutorialContainer = this.add.container(640, 500).setDepth(120);
        const tutBg = this.add.rectangle(0, 0, 700, 200, 0x000000, 0.85);
        tutBg.setStrokeStyle(4, 0x00ffff);

        const tutTitle = this.add.text(0, -60, 'CONTROLS TUTORIAL', {
            fontFamily: '"Press Start 2P"', fontSize: 36, color: '#ffff00'
        }).setOrigin(0.5);

        const tutKeyboard = this.add.text(-180, 20, 'KEYBOARD\n[↑][↓][←][→] : Move\n[Z] : Button 1 (Action)\n[X] : Button 2 (Cancel)', {
            fontFamily: '"Press Start 2P"', fontSize: 12, color: '#ffffff', align: 'center'
        }).setOrigin(0.5);

        const tutGamepad = this.add.text(180, 20, 'GAMEPAD\nD-PAD / L-STICK : Move\n[A] Face Button : Action\n[B] Face Button : Cancel', {
            fontFamily: '"Press Start 2P"', fontSize: 12, color: '#00ffff', align: 'center'
        }).setOrigin(0.5);

        this.tutorialContainer.add([tutBg, tutTitle, tutKeyboard, tutGamepad]);
        this.cameras.main.ignore(this.tutorialContainer);

        this.gameStarted = false;

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

    generateArcadeTextures() {
        // Player Texture (Cyan Mage with a golden hat)
        const pGraphics = this.add.graphics();
        pGraphics.fillStyle(0x00ffff, 1);
        pGraphics.fillRect(2, 4, 12, 12); // body
        pGraphics.fillStyle(0xffd700, 1);
        pGraphics.fillRect(4, 0, 8, 4); // crown/hat
        pGraphics.generateTexture('player', 16, 16);
        pGraphics.destroy();

        // Enemy Texture (Goblin / Demon style)
        const eGraphics = this.add.graphics();
        eGraphics.fillStyle(0xff0044, 1);
        eGraphics.fillRect(0, 0, 14, 14);
        eGraphics.fillStyle(0x00ff00, 1);
        eGraphics.fillRect(2, 4, 4, 4); // left eye
        eGraphics.fillRect(8, 4, 4, 4); // right eye
        eGraphics.generateTexture('enemy', 14, 14);
        eGraphics.destroy();

        // Projectile / Magic Bolt Texture
        const projGraphics = this.add.graphics();
        projGraphics.fillStyle(0xffff00, 1);
        projGraphics.fillRect(0, 0, 8, 8);
        projGraphics.generateTexture('projectile', 8, 8);
        projGraphics.destroy();

        // XP Gem (Cyan/Magenta diamond)
        const gemGraphics = this.add.graphics();
        gemGraphics.fillStyle(0xff00ff, 1);
        gemGraphics.fillRect(2, 2, 6, 6);
        gemGraphics.generateTexture('gem', 10, 10);
        gemGraphics.destroy();
    }

    createHUD() {

        this.uiContainer = this.add.container(0, 0);

        this.scoreText = this.add.text(30, 30, 'SCORE: 0', {
            fontFamily: '"Press Start 2P"', fontSize: 24, color: '#00ffff',
            stroke: '#000000', strokeThickness: 4
        }).setDepth(100);

        this.levelText = this.add.text(30, 70, 'LVL: 1', {
            fontFamily: '"Press Start 2P"', fontSize: 24, color: '#ffff00',
            stroke: '#000000', strokeThickness: 4
        }).setDepth(100);

        const hpLabel = this.add.text(300, 30, 'HP:', {
            fontFamily: '"Press Start 2P"', fontSize: 24, color: '#ffffff'
        }).setDepth(100);

        this.hpBarBg = this.add.rectangle(350, 42, 300, 20, 0x440000).setOrigin(0, 0.5).setDepth(100);
        this.hpBar = this.add.rectangle(350, 42, 300, 20, 0xff0000).setOrigin(0, 0.5).setDepth(100);

        const xpLabel = this.add.text(300, 70, 'XP:', {
            fontFamily: '"Press Start 2P"', fontSize: 24, color: '#ffffff'
        }).setDepth(100);

        this.xpBarBg = this.add.rectangle(350, 82, 300, 20, 0x004444).setOrigin(0, 0.5).setDepth(100);
        this.xpBar = this.add.rectangle(350, 82, 0, 20, 0x00ffff).setOrigin(0, 0.5).setDepth(100);

        // Announcement banner text
        this.announcer = this.add.text(640, 400, '', {
            fontFamily: '"Press Start 2P"', fontSize: 48, color: '#ffd700',
            stroke: '#000000', strokeThickness: 8, align: 'center'
        }).setOrigin(0.5).setDepth(110);

        this.uiContainer.add([this.scoreText, this.levelText, hpLabel, this.hpBarBg, this.hpBar, xpLabel, this.xpBarBg, this.xpBar, this.announcer]);
        this.cameras.main.ignore(this.uiContainer);
    }

    announce(msg, duration = 2000) {
        this.announcer.setText(msg);
        this.time.delayedCall(duration, () => {
            this.announcer.setText('');
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
            left: rawPad.left,
            right: rawPad.right,
            up: rawPad.up,
            down: rawPad.down,
            axes: rawPad.axes,
            buttons: rawPad.buttons
        } : null;

        // Cheat code check
        const keys = [
            { key: this.cursors.up, val: 'UP' },
            { key: this.cursors.down, val: 'DOWN' },
            { key: this.cursors.left, val: 'LEFT' },
            { key: this.cursors.right, val: 'RIGHT' },
            { key: this.keys.x, val: 'X' },
            { key: this.keys.z, val: 'Z' }
        ];

        for (const k of keys) {
            if (Phaser.Input.Keyboard.JustDown(k.key)) {
                this.inputBuffer.push(k.val);
                if (this.inputBuffer.length > 10) this.inputBuffer.shift();

                const target = ['UP', 'UP', 'DOWN', 'DOWN', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'X', 'Z'];
                if (this.inputBuffer.join(',') === target.join(',')) {
                    if (!this.cheatActive) {
                        this.cheatActive = true;
                        this.announce("CHEAT ACTIVATED!\nRetro Vision Mode!", 3000);

                        const rand = Math.floor(Math.random() * 4);
                        if (rand === 0) this.cameras.main.postFX.addColorMatrix().grayscale();
                        else if (rand === 1) this.cameras.main.postFX.addColorMatrix().sepia();
                        else if (rand === 2) this.cameras.main.postFX.addColorMatrix().negative();
                        else this.cameras.main.postFX.addColorMatrix().night(); // GameBoy green tone

                        this.time.delayedCall(10000, () => {
                            this.cameras.main.postFX.clear();
                            this.cameras.main.setPostPipeline('CRTPipeline');
                            this.cheatActive = false;
                        });
                    }
                }
            }
        }

        // Actions
        if (Phaser.Input.Keyboard.JustDown(this.keys.h) || (pad && pad.isButtonDown(8))) {
            window.parent.postMessage({ action: "GO_HOME" }, '*');
        }

        if (Phaser.Input.Keyboard.JustDown(this.keys.r) || (pad && pad.isButtonDown(9))) {
            window.parent.postMessage({ action: 'RELOAD_GAME' }, '*');
        }

        if (this.playerStats.currentHp <= 0) {
            return; // Game over, stop moving & attacks
        }

        if (!this.gameStarted) {
            const anyKey = this.cursors.left.isDown || this.cursors.right.isDown ||
                this.cursors.up.isDown || this.cursors.down.isDown ||
                this.keys.a.isDown || this.keys.d.isDown ||
                this.keys.w.isDown || this.keys.s.isDown ||
                this.keys.z.isDown || this.keys.x.isDown;
            const anyPad = pad && (pad.buttons.some(b => b.pressed) || pad.axes.some(a => Math.abs(a.value) > 0.5));

            if (anyKey || anyPad) {
                this.gameStarted = true;
                this.lastSpawnTime = time;
                this.lastShotTime = time;

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

        // 1. Player Movement (4-way WASD / Cursors / Gamepad)
        let moveX = 0;
        let moveY = 0;

        if (this.cursors.left.isDown || this.keys.a.isDown || (pad && (pad.left || pad.axes[0].value < -0.5))) moveX = -1;
        else if (this.cursors.right.isDown || this.keys.d.isDown || (pad && (pad.right || pad.axes[0].value > 0.5))) moveX = 1;

        if (this.cursors.up.isDown || this.keys.w.isDown || (pad && (pad.up || pad.axes[1].value < -0.5))) moveY = -1;
        else if (this.cursors.down.isDown || this.keys.s.isDown || (pad && (pad.down || pad.axes[1].value > 0.5))) moveY = 1;

        // Normalize and apply movement speed
        if (moveX !== 0 || moveY !== 0) {
            const len = Math.sqrt(moveX * moveX + moveY * moveY);
            this.player.x += (moveX / len) * (this.playerStats.speed * delta / 1000);
            this.player.y += (moveY / len) * (this.playerStats.speed * delta / 1000);

            // Prevent moving out of 320x240 logical bounds
            this.player.x = Phaser.Math.Clamp(this.player.x, 8, 312);
            this.player.y = Phaser.Math.Clamp(this.player.y, 8, 232);

            this.rangeRing.x = this.player.x;
            this.rangeRing.y = this.player.y;
        }

        // 2. Enemy Spawning & Chasing logic
        if (time > this.lastSpawnTime + this.spawnInterval) {
            this.spawnEnemy();
            this.lastSpawnTime = time;
        }

        // Move enemies toward player
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const enemy = this.enemies[i];
            if (!enemy.active) continue;

            // Chasing direction
            const dx = this.player.x - enemy.x;
            const dy = this.player.y - enemy.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist > 1) {
                enemy.x += (dx / dist) * (enemy.speed * delta / 1000);
                enemy.y += (dy / dist) * (enemy.speed * delta / 1000);
            }

            // Damage collision with Player
            if (dist < 12) {
                this.playerStats.currentHp -= 0.5;
                this.cameras.main.shake(50, 0.01);
                this.updateHUD();
                if (this.playerStats.currentHp <= 0) {
                    this.announce("GAME OVER!\nRefresh to retry", 10000);
                    this.player.setTint(0xff0000);
                    window.parent.postMessage({
                        type: 'game-over',
                        score: this.playerStats.score
                    }, '*');
                }
            }
        }

        // 3. Auto-Attack: Fire projectile at the nearest enemy
        if (time > this.lastShotTime + this.playerStats.fireDelay) {
            this.fireProjectile();
            this.lastShotTime = time;
        }

        // 4. Update Projectiles (Flying & Enemy Collisions)
        for (let i = this.projectiles.length - 1; i >= 0; i--) {
            const p = this.projectiles[i];
            p.x += p.vx * delta / 1000;
            p.y += p.vy * delta / 1000;

            // Out of bounds check
            if (p.x < 0 || p.x > 320 || p.y < 0 || p.y > 240) {
                p.destroy();
                this.projectiles.splice(i, 1);
                continue;
            }

            // Collision with enemies
            for (let j = this.enemies.length - 1; j >= 0; j--) {
                const enemy = this.enemies[j];
                const dist = Phaser.Math.Distance.Between(p.x, p.y, enemy.x, enemy.y);

                if (dist < 10) {
                    enemy.hp -= this.playerStats.damage;
                    p.destroy();
                    this.projectiles.splice(i, 1);

                    if (enemy.hp <= 0) {
                        // Drop XP gem, spawn particle/flash effect
                        this.createExplosion(enemy.x, enemy.y);
                        this.createGem(enemy.x, enemy.y);
                        enemy.destroy();
                        this.enemies.splice(j, 1);
                        this.playerStats.score += 10;
                        this.updateHUD();
                    }
                    break;
                }
            }
        }

        // 5. XP Gems Collection (Magnet force if close)
        for (let i = this.xpGems.length - 1; i >= 0; i--) {
            const gem = this.xpGems[i];
            const dist = Phaser.Math.Distance.Between(gem.x, gem.y, this.player.x, this.player.y);

            // Strong magnet effect when player approaches
            if (dist < 40) {
                gem.x += ((this.player.x - gem.x) / dist) * 150 * delta / 1000;
                gem.y += ((this.player.y - gem.y) / dist) * 150 * delta / 1000;
            }

            // Collect gem
            if (dist < 8) {
                gem.destroy();
                this.xpGems.splice(i, 1);
                this.gainXP(15);
            }
        }

        // Draw low-res world to buffer (Keep at bottom of update)
        this.gameBuffer.clear();
        this.gameBuffer.draw(this.gameLayer);
    }

    spawnEnemy() {
        // Spawn off-screen slightly beyond the 320x240 border
        const angle = Math.random() * Math.PI * 2;
        const distance = 200; // Away from the center

        const sx = 160 + Math.cos(angle) * distance;
        const sy = 120 + Math.sin(angle) * distance;

        const enemy = this.add.sprite(sx, sy, 'enemy').setDepth(5);
        enemy.hp = 20 + (this.playerStats.level * 5);
        enemy.speed = 30 + Math.random() * 20;

        this.gameLayer.add(enemy);
        this.enemies.push(enemy);
    }

    fireProjectile() {
        if (this.enemies.length === 0) return;

        // Find nearest enemy
        let nearest = null;
        let minDist = Infinity;

        for (const enemy of this.enemies) {
            const dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, enemy.x, enemy.y);
            if (dist < minDist) {
                minDist = dist;
                nearest = enemy;
            }
        }

        if (nearest && minDist <= 70) {
            // Spawn magic bolt
            const p = this.add.sprite(this.player.x, this.player.y, 'projectile').setDepth(8);
            this.gameLayer.add(p);

            // Calculate trajectory velocities (Speed 250px/s)
            const angle = Phaser.Math.Angle.Between(this.player.x, this.player.y, nearest.x, nearest.y);
            p.vx = Math.cos(angle) * 250;
            p.vy = Math.sin(angle) * 250;

            this.projectiles.push(p);
        }
    }

    createGem(x, y) {
        const gem = this.add.sprite(x, y, 'gem').setDepth(4);
        this.gameLayer.add(gem);
        this.xpGems.push(gem);
    }

    gainXP(amt) {
        this.playerStats.xp += amt;
        if (this.playerStats.xp >= this.playerStats.xpToNextLevel) {
            // Level up!
            this.playerStats.level += 1;
            this.playerStats.xp -= this.playerStats.xpToNextLevel;
            this.playerStats.xpToNextLevel = Math.floor(this.playerStats.xpToNextLevel * 1.5);

            // Upgrade stats
            this.playerStats.damage += 5;
            this.playerStats.fireDelay = Math.max(150, this.playerStats.fireDelay - 50);

            this.announce("LEVEL UP!\nDamage & Fire Rate Boosted!", 2500);
        }

        this.updateHUD();
    }

    updateHUD() {
        this.scoreText.setText(`SCORE: ${this.playerStats.score}`);
        this.levelText.setText(`LVL: ${this.playerStats.level}`);

        // Health Bar Update
        const hpPct = Math.max(0, this.playerStats.currentHp / this.playerStats.maxHp);
        this.hpBar.width = 300 * hpPct;

        // XP Bar Update
        const xpPct = Math.min(1, this.playerStats.xp / this.playerStats.xpToNextLevel);
        this.xpBar.width = 300 * xpPct;
    }

    createExplosion(x, y, color = 0xff0044) {
        const emitter = this.add.particles(x, y, 'gem', {
            speed: { min: 50, max: 150 },
            angle: { min: 0, max: 360 },
            scale: { start: 0.5, end: 0 },
            lifespan: 400,
            quantity: 8,
            stopAfter: 8,
            tint: color
        });
        this.gameLayer.add(emitter);
        this.time.delayedCall(500, () => {
            emitter.destroy();
        });
    }
}
