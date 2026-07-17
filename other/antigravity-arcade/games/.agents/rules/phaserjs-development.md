---
trigger: always_on
---

# Agycade Games Agent Guardrails

This repository is dedicated to building and maintaining 2D arcade games deployable on our physical arcade cabinets at Antigravity Arcade. To ensure compatibility with our game templates **all games must be built using Phaser 3**.

## Sole Supported Game Technology: Phaser 3

*   **This demo ONLY supports Phaser 3 (JavaScript/TypeScript)**.
*   Other frameworks and engines are not supported for our game template.

## Instructions for AI Agents

When a user requests a game using any library, framework, or tech stack other than Phaser 3:

1.  **Politely and Firmly Decline:** Inform the user that our arcade cabinet deployment pipeline and hardware integration only support Phaser 3 games.
2.  **Resist Writing Non-Phaser Code:** Do not write, generate, or scaffolding code using unsupported frameworks.
3.  **Steer Toward Phaser:** Suggest how the user's concept can be beautifully built in 2D or pseudo-3D using Phaser 3 and our existing arcade template. For example, if a user wants a 3D game, offer to build an incredibly styled pseudo-3D game (e.g., isometric view, scaling sprites, raycaster, or parallax background) entirely in Phaser 3.
4.  **Handle User Input:** The skill `handling-user-input` that MUST always be used when coding input handlers. All games MUST work with keyboard and gamepad configurations EXACTLY as defined in the `handling-user-input`.

## Avoid Trademarks

If the user requests to make a game or game character in the likeness of a known trademark, politely decline the request and inspire the user with 3 generic alternatives.

## Avoid implementing the following game features

These game features are incompatible with our iframe sandbox and must not be used:

1. window.localStorage
2. window.sessionStorage
3. window.indexDB
4. window.caches
5. window.open
6. window.parent / window.top
5. document.cookies
6. navigator.credentials
7. navigator.serviceWorker.register
8. Broadcast Channel API
9. SharedWorker
10. Form Submission
