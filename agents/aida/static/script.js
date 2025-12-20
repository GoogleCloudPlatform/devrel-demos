const messagesDiv = document.getElementById('messages');
const messageText = document.getElementById('message-text');
const avatarImg = document.getElementById('avatar-img');
const avatarLabel = document.getElementById('avatar-label');
const systemLog = document.getElementById('system-log');
const logWindow = document.getElementById('system-log-window');
const contextLabel = document.getElementById('context-label');
const contextBar = document.getElementById('context-bar');

let debugMode = false;

function logActivity(message, type = 'info') {
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `<span class="log-time">[${timeStr}]</span> <span class="log-sys">${message}</span>`;
    systemLog.appendChild(entry);
    logWindow.scrollTop = logWindow.scrollHeight;
}

function toggleDebug() {
    debugMode = !debugMode;
    const btn = document.getElementById('debug-toggle');
    btn.textContent = `DEBUG: ${debugMode ? 'ON' : 'OFF'}`;
    btn.classList.toggle('active', debugMode);
    logActivity(`DEBUG MODE: ${debugMode ? 'ENABLED' : 'DISABLED'}`);
}

async function updateContextMeter() {
    try {
        const response = await fetch('/session/usage');
        const data = await response.json();
        // data has prompt_tokens, completion_tokens, total_tokens, max_tokens
        const total = data.total_tokens || 0;
        const max = data.max_tokens || 1000000;
        const percentage = Math.min(100, (total / max) * 100).toFixed(1);
        
        contextLabel.textContent = `${percentage}% (${total.toLocaleString()} / ${(max/1000).toFixed(0)}k)`;
        contextBar.style.width = `${percentage}%`;
        
        // Color coding based on usage
        if (percentage >= 100) {
            contextBar.style.backgroundColor = 'var(--pc98-red)';
        } else if (percentage >= 80) {
            contextBar.style.backgroundColor = 'var(--pc98-amber)';
        } else {
            contextBar.style.backgroundColor = 'var(--pc98-green)';
        }
    } catch (e) {
        console.error("Failed to update context meter:", e);
    }
}

async function fetchCurrentModel() {
    try {
        const response = await fetch('/config/model');
        const data = await response.json();
        if (data.model_id) {
            updateActiveModelButton(data.model_id);
            if (debugMode) {
                logActivity(`DEBUG: Initial model set to ${data.model_id}`);
            }
        }
    } catch (e) {
        console.error("Failed to fetch current model:", e);
    }
}

// Boot sequence: Immediate ready state
async function bootSequence() {
    logActivity("AIDA AGENT READY.");
    updateContextMeter();
    fetchCurrentModel();
}

// Start boot sequence
bootSequence();

// Idle blinking logic
let blinkInterval = null;
function startBlinking() {
    if (blinkInterval) return;
    // Blink every 4-8 seconds randomly (slower)
    blinkInterval = setTimeout(function blink() {
        avatarImg.src = '/blink';
        setTimeout(() => {
            // Only switch back to idle if we are still in ONLINE state
            if (avatarLabel.textContent === "STATUS: ONLINE") {
                    avatarImg.src = '/idle';
            }
        }, 300); // Eyes closed for 300ms
        blinkInterval = setTimeout(blink, Math.random() * 4000 + 4000);
    }, 4000);
}

function stopBlinking() {
    if (blinkInterval) {
        clearTimeout(blinkInterval);
        blinkInterval = null;
    }
}

// Start blinking initially
startBlinking();

function sendShortcut(command) {
    messageText.value = command;
    // Create a synthetic submit event
    const event = new Event('submit', { cancelable: true });
    const form = document.getElementById('user-input');
    form.dispatchEvent(event);
    // Call sendMessage directly as dispatchEvent might not trigger the onsubmit handler if attached via HTML attribute in some browsers, 
    // but here it is attached via onsubmit attribute.
    // Actually, let's just call sendMessage directly with a mock event.
    sendMessage({ preventDefault: () => {} });
}

async function typeOutHTML(container, html) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    async function typeNode(node, parent) {
        if (node.nodeType === Node.TEXT_NODE) {
            for (const char of node.textContent) {
                parent.append(char);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                await new Promise(r => setTimeout(r, 5)); // Faster typing
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            const el = document.createElement(node.tagName);
            // Copy attributes
            for (const attr of node.attributes) {
                el.setAttribute(attr.name, attr.value);
            }
            parent.appendChild(el);
            for (const child of node.childNodes) {
                await typeNode(child, el);
            }
        }
    }
    
    for (const child of tempDiv.childNodes) {
        await typeNode(child, container);
    }
}

function updateActiveModelButton(modelId) {
    document.querySelectorAll('#model-row button').forEach(btn => btn.classList.remove('active'));
    if (modelId === 'gemini') {
        document.getElementById('btn-gemini').classList.add('active');
    } else if (modelId === 'qwen') {
        document.getElementById('btn-qwen').classList.add('active');
    } else if (modelId === 'gpt-oss') {
        document.getElementById('btn-gpt').classList.add('active');
    }
}

async function sendMessage(event) {
    event.preventDefault();
    const query = messageText.value;
    if (!query) return;

    // Display user message
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'user-message';
    userMsgDiv.textContent = `> ${query}`;
    messagesDiv.appendChild(userMsgDiv);
    messageText.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Handle slash commands
    if (query.startsWith('/model ')) {
        const modelId = query.split(' ')[1];
        logActivity(`COMMAND: SWITCHING MODEL TO '${modelId}'...`);
        try {
            const response = await fetch('/config/model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId })
            });
            const data = await response.json();
            if (data.status === 'ok') {
                logActivity(`SUCCESS: MODEL SWITCHED TO ${data.current_model}`);
                updateActiveModelButton(modelId);
                const agentMsgDiv = document.createElement('div');
                agentMsgDiv.className = 'agent-message';
                agentMsgDiv.textContent = `[SYSTEM] Model switched successfully.`;
                messagesDiv.appendChild(agentMsgDiv);
                updateContextMeter(); // Update meter as max_tokens might have changed
            } else {
                logActivity(`ERROR: ${data.error}`, 'error');
                 const agentMsgDiv = document.createElement('div');
                agentMsgDiv.className = 'agent-message';
                agentMsgDiv.textContent = `[SYSTEM] Error: ${data.error}`;
                messagesDiv.appendChild(agentMsgDiv);
            }
        } catch (e) {
            logActivity(`ERROR: FAILED TO SWITCH MODEL`, 'error');
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return;
    }

    if (query === '/clear') {
        logActivity("COMMAND: CLEARING SESSION MEMORY...");
        try {
             const response = await fetch('/session/clear', { method: 'POST' });
             const data = await response.json();
             logActivity(`SUCCESS: ${data.message}`);
             messagesDiv.innerHTML = ''; // Clear chat window
             updateContextMeter(); // Reset meter immediately
        } catch (e) {
             logActivity("ERROR: FAILED TO CLEAR SESSION", 'error');
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return;
    }

    if (query === '/debug') {
        logActivity("COMMAND: TOGGLING DEBUG MODE...");
        toggleDebug();
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return;
    }

    logActivity(`INPUT RECEIVED: "${query.substring(0, 20)}${query.length > 20 ? '...' : ''}"`);

    // Create a container for the agent's response
    const agentMsgDiv = document.createElement('div');
    agentMsgDiv.className = 'agent-message';
    messagesDiv.appendChild(agentMsgDiv);

    stopBlinking();
    avatarImg.src = '/think'; // Set to thinking pose
    avatarLabel.textContent = "STATUS: THINKING";
    avatarLabel.style.color = "var(--pc98-cyan)";
    logActivity("AGENT STATUS: THINKING...");

    // Thinking animation
    let thinkBlinkInterval = setInterval(() => {
            avatarImg.src = '/think_blink';
            setTimeout(() => {
                if (avatarLabel.textContent === "STATUS: THINKING") {
                    avatarImg.src = '/think';
                }
            }, 300);
    }, 3500);

    try {
        // Stream agent response
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let isStreaming = true;

        let animationInterval = null;

        function startTalkingAnimation() {
            if (animationInterval) return;
            clearInterval(thinkBlinkInterval); // Stop thinking animation
            let toggle = false;
            avatarImg.src = '/talk';
            avatarLabel.textContent = "STATUS: RESPONDING";
            avatarLabel.style.color = "var(--pc98-green)";
            // logActivity("AGENT STATUS: RESPONDING..."); 
            animationInterval = setInterval(() => {
                toggle = !toggle;
                avatarImg.src = toggle ? '/talk' : '/idle';
            }, 150);
        }

        function stopAnimation() {
            clearInterval(thinkBlinkInterval); // Ensure stopped
            if (animationInterval) {
                clearInterval(animationInterval);
                animationInterval = null;
            }
            avatarImg.src = '/idle';
            avatarLabel.textContent = "STATUS: ONLINE";
            avatarLabel.style.color = "var(--pc98-green)";
            logActivity("AGENT STATUS: IDLE.");
            startBlinking();
        }

        // Asynchronously read from the stream
        (async () => {
            let fullMarkdown = "";
            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    // Render and type out the full response
                    const fullHTML = DOMPurify.sanitize(marked.parse(fullMarkdown));
                    agentMsgDiv.innerHTML = ''; // Clear loading indicator
                    await typeOutHTML(agentMsgDiv, fullHTML);
                    
                    stopAnimation();
                    updateContextMeter(); // Update meter after response finishes
                    break;
                }
                buffer += decoder.decode(value, { stream: true });
                
                // Process complete lines from buffer
                let lineEnd;
                while ((lineEnd = buffer.indexOf('\n')) !== -1) {
                    const line = buffer.substring(0, lineEnd).trim();
                    buffer = buffer.substring(lineEnd + 1);
                    if (line) {
                        try {
                            const data = JSON.parse(line);
                            if (data.type === 'log') {
                                logActivity(data.content);
                            } else if (data.type === 'tool_output') {
                                if (debugMode) {
                                    logActivity(`TOOL OUTPUT: ${data.content}`);
                                }
                            } else if (data.type === 'text') {
                                startTalkingAnimation();
                                fullMarkdown += data.content;
                                // Show a simple loading indicator while accumulating
                                agentMsgDiv.textContent = "Receiving transmission...";
                            }
                        } catch (e) {
                            console.error("Error parsing JSON line:", line, e);
                        }
                    }
                }
            }
        })();

    } catch (e) {
        clearInterval(thinkBlinkInterval); // Stop thinking animation on error
        avatarImg.src = '/error';
        avatarLabel.textContent = "STATUS: ERROR";
        avatarLabel.style.color = "var(--pc98-red)";
        agentMsgDiv.textContent = "ERROR: CONNECTION LOST";
        logActivity("ERROR: CONNECTION LOST!", "error");
        // startBlinking(); // Don't blink in error state
    }
}