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

import StartGame from './game/main';

document.addEventListener('DOMContentLoaded', () => {
    // Wait for the retro font to load before booting the game to avoid fallback fonts
    document.fonts.load('10px "Press Start 2P"').then(() => {
        StartGame('game-container');
    }).catch(err => {
        console.error('Font failed to load:', err);
        StartGame('game-container'); // Fallback
    });
});

// Listen for screenshot requests from the parent window (for moderation)
window.addEventListener('message', (event) => {
    if (event.data && event.data.action === 'CAPTURE_SCREENSHOT') {
        const canvas = document.querySelector('canvas');
        if (canvas) {
            const dataURL = canvas.toDataURL('image/png');
            window.parent.postMessage({
                action: 'SCREENSHOT_DATA',
                data: dataURL
            }, '*');
        }
    }
});
