---
name: messaging-game-over
description: Ensures games created have a lose condition and send a message to the parent iframe in a standardized manner. Use when creating or modifying a game.
---

# Game Structure and iframe messaging

Follow these steps when creating a new game:

1. **Lose condition**
   Ensure the game loop always has a "lose condition" that can be reached in which the player has failed.

2. **Iframe message**
   When the failure state is reached, use the iframe post message feature to send a message from the current page up to the parent page of the site in the following format:

   window.parent.postMessage({
    type: 'game-over',
    score: this.score,
   }, '*');

