document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const stopButton = document.getElementById('stop-button');
    const messageList = document.getElementById('message-list');
    const chatContainer = document.querySelector('.chat-container');

    let prevScrollHeight = chatContainer.scrollHeight;

    const resizeObserver = new ResizeObserver(() => {
        const newScrollHeight = chatContainer.scrollHeight;
        const wasAtBottom = prevScrollHeight - chatContainer.clientHeight <= chatContainer.scrollTop + 50;

        if (wasAtBottom) {
            chatContainer.scrollTop = newScrollHeight;
        }
        prevScrollHeight = newScrollHeight;
    });
    resizeObserver.observe(messageList);

    const fileUpload = document.getElementById('file-upload');
    const attachmentPreview = document.getElementById('attachment-preview');
    const previewImg = document.getElementById('preview-img');
    const previewVid = document.getElementById('preview-vid');
    const removeAttachment = document.getElementById('remove-attachment');

    let currentAttachment = null;

    const userId = "default_user";
    localStorage.setItem('adk_user_id', userId);

    let sessionId = localStorage.getItem('adk_current_session_id');

    let appName = "agent"; // Default

    async function loadConfig() {
        try {
            const res = await fetch('/config');
            if (res.ok) {
                const config = await res.json();
                appName = config.appName || appName;
                
                // Update header with app info
                const appTitleEl = document.getElementById('app-title');
                const appDescEl = document.getElementById('app-desc');
                
                if (appTitleEl) appTitleEl.textContent = appName;
                if (appDescEl) appDescEl.textContent = config.description || '';
                document.title = `${appName}  - ADK Agent Client`;
            }
        } catch (e) {
            console.error('Failed to load config:', e);
        }
    }

    let sessionStates = {}; // { sessionId: { messageElements: Element[], input: string, ... } }
    let currentToolName = 'Tool';
    const activeConnections = new Set();

    function getSessionState(id) {
        if (!sessionStates[id]) {
            sessionStates[id] = {
                sessionId: id,
                messageElements: [],
                input: '',
                currentBlockType: null,
                currentBlockElement: null,
                isThinking: false,
                accumulatedThoughts: '',
                currentThinkingContainer: null,
                toolFailed: false,
                isStreaming: false,
                currentReader: null
            };
        }
        return sessionStates[id];
    }

    function updateStatus(text, type, targetSessionId) {
        if (!targetSessionId) return;

        const sessionItem = sessionListContainer.querySelector(`.session-item[title="${targetSessionId}"]`);
        if (!sessionItem) return;

        let indicator = sessionItem.querySelector('.session-status-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.className = 'session-status-indicator';
            sessionItem.appendChild(indicator);
        }

        if (activeConnections.has(targetSessionId)) {
            if (!indicator.querySelector('.spinner')) {
                indicator.innerHTML = `
                    <svg class="spinner" viewBox="0 0 50 50">
                        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                    </svg>
                `;
            }
        } else {
            indicator.innerHTML = '';
        }

        // Update input line indicator if this is the current session
        if (targetSessionId === sessionId) {
            const inputIndicator = document.getElementById('input-status-indicator');
            if (inputIndicator) {
                if (activeConnections.has(targetSessionId)) {
                    if (!inputIndicator.querySelector('.spinner')) {
                        inputIndicator.innerHTML = `
                            <svg class="spinner" viewBox="0 0 50 50">
                                <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                            </svg>
                        `;
                    }
                } else {
                    inputIndicator.innerHTML = '';
                }
            }
        }
    }

    const sessionListContainer = document.getElementById('session-list');
    const newSessionButton = document.getElementById('new-session-button');

    function saveCurrentSessionState() {
        if (sessionId) {
            const state = getSessionState(sessionId);
            state.input = chatInput.value;
        }
    }

    async function loadSessions() {
        try {
            const response = await fetch(`/apps/${appName}/users/${userId}/sessions`);
            if (!response.ok) throw new Error('Failed to fetch sessions');
            const sessions = await response.json();

            // Fetch missing timestamps in parallel and cache them
            await Promise.all(sessions.map(async (s) => {
                let time = localStorage.getItem(`session_time_${s.id}`);
                if (!time) {
                    try {
                        const res = await fetch(`/apps/${appName}/users/${userId}/sessions/${s.id}`);
                        if (res.ok) {
                            const data = await res.json();
                            time = data.lastUpdateTime || Date.now();
                            localStorage.setItem(`session_time_${s.id}`, time);
                        }
                    } catch (e) {
                        console.error(`Failed to fetch details for session ${s.id}`, e);
                    }
                }
                s.lastUpdateTime = parseFloat(time) || 0;
            }));

            // Sort by last update time descending (newest first)
            sessions.sort((a, b) => b.lastUpdateTime - a.lastUpdateTime);

            renderSessionList(sessions);
            return sessions;
        } catch (error) {
            console.error('Error loading sessions:', error);
            return [];
        }
    }

    function renderSessionList(sessions) {
        if (!sessionListContainer) return;
        sessionListContainer.innerHTML = '';



        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'session-item';
            if (session.id === sessionId) {
                item.classList.add('active');
            }
            item.title = session.id;

            const textSpan = document.createElement('span');
            textSpan.textContent = session.id.substring(0, 15) + '...';
            item.appendChild(textSpan);

            const indicator = document.createElement('span');
            indicator.className = 'session-status-indicator';

            if (activeConnections.has(session.id)) {
                indicator.innerHTML = `
                    <svg class="spinner" viewBox="0 0 50 50">
                        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                    </svg>
                `;
            }

            item.appendChild(indicator);

            item.addEventListener('click', () => switchSession(session.id));
            sessionListContainer.appendChild(item);
        });
    }

    async function switchSession(newSessionId) {
        if (newSessionId === sessionId) return;

        saveCurrentSessionState();

        sessionId = newSessionId;
        localStorage.setItem('adk_current_session_id', sessionId);

        // Update active class in UI
        const items = sessionListContainer.querySelectorAll('.session-item');
        items.forEach(item => {
            if (item.title === sessionId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Update input line indicator
        const inputIndicator = document.getElementById('input-status-indicator');
        if (inputIndicator) {
            if (activeConnections.has(sessionId)) {
                inputIndicator.innerHTML = `
                    <svg class="spinner" viewBox="0 0 50 50">
                        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                    </svg>
                `;
            } else {
                inputIndicator.innerHTML = '';
            }
        }

        const state = getSessionState(sessionId);
        if (state.messageElements.length > 0) {
            messageList.innerHTML = '';
            state.messageElements.forEach(el => messageList.appendChild(el));
            chatInput.value = state.input || '';
            prevScrollHeight = chatContainer.scrollHeight;
            chatContainer.scrollTop = chatContainer.scrollHeight;
        } else {
            await reloadCurrentSession();
        }
    }

    async function reloadCurrentSession() {
        messageList.innerHTML = '<div class="message system-message"><div class="message-content">Loading history...</div></div>';
        chatInput.value = '';
        prevScrollHeight = chatContainer.scrollHeight;

        try {
            const response = await fetch(`/apps/${appName}/users/${userId}/sessions/${sessionId}`);
            if (response.ok) {
                const sessionData = await response.json();
                renderSessionHistory(sessionData.events);
            } else {
                messageList.innerHTML = `
                    <div class="message system-message">
                        <div class="message-content">
                            How can I help you today?
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading session history:', error);
            messageList.innerHTML = '<div class="message system-message"><div class="message-content">Error loading history.</div></div>';
        }
    }

    function renderSessionHistory(events) {
        messageList.innerHTML = '';
        if (!events || events.length === 0) {
            messageList.innerHTML = `
                <div class="message system-message">
                    <div class="message-content">
                        How can I help you today?
                    </div>
                </div>
            `;
            return;
        }

        const state = getSessionState(sessionId);
        state.messageElements = [];
        let currentAgentDiv = null;
        state.currentAgentAuthor = null;

        // Deduplicate cumulative incremental events
        let filteredEvents = [];
        for (let i = 0; i < events.length; i++) {
            const curr = events[i];
            const next = events[i + 1];
            
            const currRole = curr.role || (curr.content && curr.content.role);
            const nextRole = next ? (next.role || (next.content && next.content.role)) : null;

            if (next && currRole === 'agent' && nextRole === 'agent') {
                let currText = curr.text || (curr.content && curr.content.parts && curr.content.parts.map(p => p.text || p.thought || '').join(''));
                let nextText = next.text || (next.content && next.content.parts && next.content.parts.map(p => p.text || p.thought || '').join(''));
                
                if (currText && nextText && nextText.startsWith(currText) && nextText !== currText) {
                    continue;
                }
            }

            // Deduplicate contiguous identical framework tool results safely!
            if (currRole === 'user') {
                let currFunc = curr.content && curr.content.parts && curr.content.parts.find(p => p.functionResponse);
                if (currFunc) {
                    let foundSubsequent = false;
                    for (let j = i + 1; j < events.length; j++) {
                        let later = events[j];
                        let laterRole = later.role || (later.content && later.content.role);
                        if (laterRole === 'user') {
                            let laterFunc = later.content && later.content.parts && later.content.parts.find(p => p.functionResponse);
                            if (laterFunc && laterFunc.functionResponse.name === currFunc.functionResponse.name) {
                                foundSubsequent = true;
                                break;
                            }
                        }
                    }
                    if (foundSubsequent) {
                        continue; // Discard stale pre-auth attempt!
                    }
                }
            }
            filteredEvents.push(curr);
        }

        filteredEvents.forEach(event => {
            const role = event.role || (event.content && event.content.role);

            if (role === 'user') {
                let isRealQuestion = event.content && event.content.parts && event.content.parts.some(p => p.text && !p.text.startsWith('[AUTH_EVENT] ') && !p.functionResponse);
                if (isRealQuestion && currentAgentDiv) {
                    if (state.isThinking) stopThinking(state);
                    currentAgentDiv = null;
                    state.currentAgentAuthor = null;
                }
                if (event.content && event.content.parts) {
                    let hasAuth = false;
                    for (const p of event.content.parts) {
                        if (p.text && p.text.startsWith('[AUTH_EVENT] ')) {
                            const text = p.text.replace('[AUTH_EVENT] ', '');
                            const successCard = document.createElement('div');
                            successCard.className = 'auth-success-card';
                            successCard.innerHTML = `<i class="fas fa-check-circle"></i> ${text}`;
                            const lastEl = state.messageElements[state.messageElements.length - 1];
                            if (lastEl) {
                                lastEl.appendChild(successCard);
                            } else {
                                messageList.appendChild(successCard);
                            }
                            hasAuth = true;
                        } else if (p.functionResponse) {
                            let skip = false;
                            if (p.functionResponse.name === 'adk_request_credential') {
                                let hasError = p.functionResponse.response && (p.functionResponse.response.error || p.functionResponse.response.oauth2?.error);
                                if (!hasError) skip = true;
                            }
                            if (!skip) {
                                const details = document.createElement('details');
                                details.classList.add('tool-call');
                                details.innerHTML = `<summary><i class="fas fa-check-circle"></i> Tool Result: ${p.functionResponse.name}</summary>
                                    <div class="tool-content">
                                        <pre><code class="language-json">${JSON.stringify(p.functionResponse.response, null, 2)}</code></pre>
                                    </div>`;
                                hljs.highlightElement(details.querySelector('code'));
                                
                                const lastEl = state.messageElements[state.messageElements.length - 1];
                                if (lastEl) {
                                    lastEl.appendChild(details);
                                } else {
                                    messageList.appendChild(details);
                                }
                            }
                        }
                    }
                    if (!hasAuth) {
                        let text = event.content.parts.filter(p => p.text && !p.text.startsWith('[AUTH_EVENT] ')).map(p => p.text).join('');
                        if (text) appendMessage('user', text, null, false);
                    }
                }
            } else {
                let hasRenderableContent = false;

                if (event.thought || (event.actions && event.actions.artifactDelta)) {
                    hasRenderableContent = true;
                }

                if (event.content && event.content.parts) {
                    for (const part of event.content.parts) {
                        if (part.thought || part.text || part.functionCall || part.functionResponse) {
                            hasRenderableContent = true;
                            break;
                        }
                    }
                }

                if (event.text) {
                    hasRenderableContent = true;
                }

                if (hasRenderableContent) {
                    let author = event.author || 'agent';
                    if (!currentAgentDiv || state.currentAgentAuthor !== author) {
                        if (state.isThinking) stopThinking(state);
                        currentAgentDiv = appendMessage('agent', '', null, false, author);
                        state.currentAgentAuthor = author;
                        state.currentBlockType = null;
                        state.currentBlockElement = null;
                        state.isThinking = false;
                        state.accumulatedThoughts = '';
                        state.accumulatedText = '';
                    }

                    processStreamData(event, currentAgentDiv, sessionId);
                }
            }
        });

        if (state.isThinking) stopThinking(state);



        prevScrollHeight = chatContainer.scrollHeight;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }



    if (newSessionButton) {
        newSessionButton.addEventListener('click', async () => {
            saveCurrentSessionState();
            try {
                const response = await fetch(`/apps/${appName}/users/${userId}/sessions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                if (!response.ok) throw new Error('Failed to create session');
                const newSession = await response.json();
                // Cache creation time
                localStorage.setItem(`session_time_${newSession.id}`, Date.now());
                switchSession(newSession.id);
                loadSessions(); // Refresh list
            } catch (error) {
                console.error('Error creating session:', error);
            }
        });
    }

    // Initial load
    (async () => {
        const loadingOverlay = document.getElementById('app-loading');
        try {
            await loadConfig();
            const sessions = await loadSessions();
            
            let exists = sessionId && sessions.some(s => s.id === sessionId);
            if (!exists) {
                if (sessions.length > 0) {
                    sessionId = sessions[0].id; // pick the most recent session
                } else {
                    sessionId = null;
                }
            }
            
            if (!sessionId) {
                try {
                    const response = await fetch(`/apps/${appName}/users/${userId}/sessions`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({})
                    });
                    if (!response.ok) throw new Error('Failed to create session');
                    const newSession = await response.json();
                    sessionId = newSession.id;
                    localStorage.setItem(`session_time_${sessionId}`, Date.now());
                } catch (error) {
                    console.error('Error creating initial session:', error);
                }
            }

            if (sessionId) {
                localStorage.setItem('adk_current_session_id', sessionId);
                const savedSessionId = sessionId;
                sessionId = null; // Force switch to load history
                await switchSession(savedSessionId);
                await loadSessions(); // Refresh session list to update active selection
            }
        } finally {
            if (loadingOverlay) {
                loadingOverlay.classList.add('hidden');
            }
        }
    })();

    // Theme Toggle
    themeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-theme');
        body.classList.toggle('light-theme');
        const isDark = body.classList.contains('dark-theme');
        themeToggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = chatInput.scrollHeight + 'px';
    });

    // File Upload Handling
    fileUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        currentAttachment = file;
        attachmentPreview.style.display = 'block';

        const reader = new FileReader();
        reader.onload = (event) => {
            if (file.type.startsWith('image/')) {
                previewImg.src = event.target.result;
                previewImg.style.display = 'block';
                previewVid.style.display = 'none';
            } else if (file.type.startsWith('video/')) {
                previewVid.src = event.target.result;
                previewVid.style.display = 'block';
                previewImg.style.display = 'none';
            }
        };
        reader.readAsDataURL(file);
    });

    removeAttachment.addEventListener('click', () => {
        currentAttachment = null;
        fileUpload.value = '';
        attachmentPreview.style.display = 'none';
        previewImg.src = '';
        previewVid.src = '';
    });

    // Send Message
    sendButton.addEventListener('click', sendMessage);
    stopButton.addEventListener('click', async () => {
        const state = getSessionState(sessionId);
        if (state.isStreaming && state.currentReader) {
            console.log(`[app.js] Stop button clicked for session ${sessionId}`);
            state.currentReader.cancel();
            state.isStreaming = false;
            
            state.messageElements = [];
            
            await reloadCurrentSession();
            
            const messageList = document.getElementById('message-list');
            const stopDiv = document.createElement('div');
            stopDiv.className = 'message system-message';
            stopDiv.innerHTML = '<div class="message-content"><i class="fas fa-stop-circle"></i> Session stopped by user.</div>';
            messageList.appendChild(stopDiv);
            
            state.messageElements.push(stopDiv);
            
            prevScrollHeight = chatContainer.scrollHeight;
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    });
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const targetSessionId = sessionId; // Capture current session ID
        console.log(`[app.js] sendMessage: initiated for session ${targetSessionId}`);
        const state = getSessionState(targetSessionId);
        if (state.isStreaming) {
            console.warn(`[app.js] sendMessage: Session ${targetSessionId} is already streaming. Ignoring request.`);
            return;
        }
        state.toolFailed = false; // Reset hard locks on manual user revisions flawlessly!
        
        sendButton.classList.add('hidden');
        stopButton.classList.remove('hidden');

        const text = chatInput.value.trim();
        if (!text && !currentAttachment) return;

        // Append user message
        appendMessage('user', text, currentAttachment);

        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Prepare request payload
        const parts = [];
        if (text) {
            parts.push({ text: text });
        }

        if (currentAttachment) {
            const base64Data = await fileToBase64(currentAttachment);
            parts.push({
                inlineData: {
                    data: base64Data.split(',')[1],
                    mimeType: currentAttachment.type
                }
            });
            // Clear attachment
            removeAttachment.click();
        }

        const payload = {
            appName: appName,
            userId: userId,
            sessionId: targetSessionId,
            newMessage: {
                role: "user",
                parts: parts
            },
            streaming: true
        };

        // Reset thinking state
        isThinking = false;
        accumulatedThoughts = '';
        currentThinkingContainer = null;
        currentThinkingContent = null;
        currentBlockType = null;
        currentBlockElement = null;

        // Create placeholder for agent message
        state.currentAgentAuthor = 'agent';
        state.currentAgentMessageDiv = appendMessage('agent', '', null, true);
        const contentDiv = state.currentAgentMessageDiv.querySelector('.message-content');

        activeConnections.add(targetSessionId);
        updateStatus('Thinking...', 'thinking', targetSessionId);

        try {
            // Use relative path to go through the proxy
            console.log(`[app.js] sendMessage: Fetching /run_sse for session ${targetSessionId}`);
            const response = await fetch(`/run_sse`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            state.currentReader = reader;
            state.isStreaming = true;
            
            const decoder = new TextDecoder();
            let buffer = '';
            let currentEventData = '';

            function handleEvent(dataStr) {
                const trimmed = dataStr.trim();
                if (trimmed === '[DONE]') return;
                try {
                    const data = JSON.parse(trimmed);
                    let author = data.author || 'agent';
                    
                    if (author !== state.currentAgentAuthor) {
                        let isPlaceholder = state.currentAgentMessageDiv.querySelector('.typing-indicator') !== null;
                        if (isPlaceholder && state.currentAgentMessageDiv.children.length === 1 && !state.currentAgentMessageDiv.querySelector('.message-author')) {
                            if (author !== 'agent' && author !== 'user') {
                                let authorDiv = document.createElement('div');
                                authorDiv.classList.add('message-author');
                                authorDiv.innerHTML = `<i class="fas fa-robot"></i> ${author}`;
                                state.currentAgentMessageDiv.insertBefore(authorDiv, state.currentAgentMessageDiv.firstChild);
                            }
                        } else {
                            if (state.isThinking) stopThinking(state);
                            state.currentAgentMessageDiv = appendMessage('agent', '', null, false, author);
                            state.currentBlockType = null;
                            state.currentBlockElement = null;
                            state.accumulatedThoughts = '';
                            state.accumulatedText = '';
                        }
                        state.currentAgentAuthor = author;
                    }
                    
                    return processStreamData(data, state.currentAgentMessageDiv, targetSessionId);
                } catch (e) {
                    console.error('Error parsing JSON from SSE:', e, 'Raw data:', trimmed);
                }
            }

            let isAuthPending = false;
            while (true) {
                const { value, done } = await reader.read();

                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (trimmedLine === '') {
                            if (currentEventData) {
                                if (handleEvent(currentEventData)) {
                                    isAuthPending = true;
                                    break;
                                }
                                currentEventData = '';
                            }
                        } else if (line.startsWith('data: ')) {
                            currentEventData += line.substring(6) + '\n';
                        }
                    }
                }

                if (isAuthPending) {
                    reader.cancel();
                    activeConnections.delete(targetSessionId);
                    updateStatus('', '', targetSessionId);
                    break;
                }

                if (done) {
                    if (buffer) {
                        if (buffer.startsWith('data: ')) {
                            currentEventData += buffer.substring(6) + '\n';
                        }
                    }
                    if (currentEventData) {
                        handleEvent(currentEventData);
                    }
                    activeConnections.delete(targetSessionId);
                    updateStatus('', '', targetSessionId);
                    break;
                }
            }

        } catch (error) {
            console.error('Error calling API:', error);
            contentDiv.innerHTML = `<span style="color: var(--google-red)">Error: Failed to connect to agent server.</span>`;
            activeConnections.delete(targetSessionId);
            updateStatus('', '', targetSessionId);
        } finally {
            state.isStreaming = false;
            state.currentReader = null;
            sendButton.classList.remove('hidden');
            stopButton.classList.add('hidden');
        }
    }

    function stopThinking(state) {
        state.isThinking = false;
        if (state.currentThinkingContainer) {
            const header = state.currentThinkingContainer.querySelector('.thinking-header');
            if (header) {
                header.innerHTML = `<i class="fas fa-brain"></i> Thought for a moment`;
            }
        }
    }

    function handleAuthRequired(toolCall, agentMessageDiv, targetSessionId) {
        console.log(`[app.js] handleAuthRequired: triggered for session ${targetSessionId}`);
        const authConfig = toolCall.args.authConfig || toolCall.args;
        const functionCallId = toolCall.id || toolCall.functionCallId;
        currentToolName = toolCall.args.toolName || toolCall.args.targetTool || 'Tool';

        const card = document.createElement('div');
        card.className = 'auth-required-card';

        const title = document.createElement('h4');
        title.innerHTML = '<i class="fas fa-lock"></i> Authorization Required';
        card.appendChild(title);

        const desc = document.createElement('p');
        desc.textContent = 'The agent requires your authorization to access external tools.';
        card.appendChild(desc);

        const loginBtn = document.createElement('button');
        loginBtn.className = 'auth-login-button';
        loginBtn.textContent = 'Sign In with Google';
        card.appendChild(loginBtn);

        agentMessageDiv.appendChild(card);

        loginBtn.addEventListener('click', () => {
            const redirectUri = window.location.origin + "/auth_callback.html";
            const authUri = authConfig.exchangedAuthCredential.oauth2.authUri + "&redirect_uri=" + encodeURIComponent(redirectUri);

            const popup = window.open(authUri, 'adk_oauth', 'width=600,height=700');
            
            let isResumingAuth = false;
            
            const popupTimer = setInterval(() => {
                if (popup.closed) {
                    clearInterval(popupTimer);
                    if (!isResumingAuth) {
                        card.innerHTML = '<div class="auth-failed-badge"><i class="fas fa-exclamation-triangle"></i> Authentication cancelled by closing popup.</div>';
                        window.removeEventListener('message', messageListener);
                        const state = getSessionState(targetSessionId);
                        state.toolFailed = true;
                    }
                }
            }, 1000);

            function messageListener(event) {
                if (event.origin !== window.location.origin) return;
                if (event.data && event.data.type === 'ADK_OAUTH_CALLBACK') {
                    console.log(`[app.js] messageListener: ADK_OAUTH_CALLBACK received for session ${targetSessionId}`);
                    if (isResumingAuth) return;
                    
                    clearInterval(popupTimer);
                    const url = event.data.url;
                    const hasError = url.includes('error=') || !url.includes('code=');
                    
                    if (hasError) {
                        card.innerHTML = '<div class="auth-failed-badge"><i class="fas fa-exclamation-triangle"></i> Authentication failed in popup!</div>';
                        const state = getSessionState(targetSessionId);
                        state.authFailed = true;
                        window.removeEventListener('message', messageListener);
                        return;
                    }
                    
                    isResumingAuth = true;
                    window.removeEventListener('message', messageListener);
                    card.innerHTML = '<div class="auth-success-spinner"><svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg> Authenticating...</div>';
                    resumeStreamAfterAuth(event.data.url, redirectUri, authConfig, functionCallId, targetSessionId, agentMessageDiv, card);
                }
            }
            window.addEventListener('message', messageListener);
        });
    }

    async function resumeStreamAfterAuth(redirectedUrl, redirectUri, authConfig, functionCallId, targetSessionId, agentMessageDiv, card) {
        const state = getSessionState(targetSessionId);
        state.currentAgentMessageDiv = agentMessageDiv;
        console.log(`[app.js] resumeStreamAfterAuth: initiated for session ${targetSessionId}`);
        sendButton.classList.add('hidden');
        stopButton.classList.remove('hidden');
        if (state.toolFailed) {
            console.warn("Session interruption: Tool failure smells. Drop early.");
            return;
        }

        authConfig.exchangedAuthCredential.oauth2.authResponseUri = redirectedUrl;
        authConfig.exchangedAuthCredential.oauth2.redirectUri = redirectUri;

        const payload = {
            appName: appName,
            userId: userId,
            sessionId: targetSessionId,
            newMessage: {
                role: "user",
                parts: [
                    {
                        text: `[AUTH_EVENT] ${currentToolName} authenticated with Google`
                    },
                    {
                        functionResponse: {
                            id: functionCallId,
                            name: 'adk_request_credential',
                            response: authConfig
                        }
                    }
                ]
            },
            streaming: true
        };

        activeConnections.add(targetSessionId);
        updateStatus('Thinking...', 'thinking', targetSessionId);

        try {
            console.log(`[app.js] resumeStreamAfterAuth: Fetching /run_sse for session ${targetSessionId}`);
            const response = await fetch(`/run_sse`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const reader = response.body.getReader();
            state.currentReader = reader;
            state.isStreaming = true;
            
            const decoder = new TextDecoder();
            let buffer = '';
            let currentEventData = '';

            function handleEvent(dataStr) {
                const trimmed = dataStr.trim();
                if (trimmed === '[DONE]') return;
                try {
                    const data = JSON.parse(trimmed);
                    let author = data.author || 'agent';

                    if (author !== state.currentAgentAuthor) {
                        let isPlaceholder = state.currentAgentMessageDiv.querySelector('.typing-indicator') !== null;
                        if (isPlaceholder && state.currentAgentMessageDiv.children.length === 1 && !state.currentAgentMessageDiv.querySelector('.message-author')) {
                            if (author !== 'agent' && author !== 'user') {
                                let authorDiv = document.createElement('div');
                                authorDiv.classList.add('message-author');
                                authorDiv.innerHTML = `<i class="fas fa-robot"></i> ${author}`;
                                state.currentAgentMessageDiv.insertBefore(authorDiv, state.currentAgentMessageDiv.firstChild);
                            }
                        } else {
                            if (state.isThinking) stopThinking(state);
                            state.currentAgentMessageDiv = appendMessage('agent', '', null, false, author);
                            state.currentBlockType = null;
                            state.currentBlockElement = null;
                            state.accumulatedThoughts = '';
                            state.accumulatedText = '';
                        }
                        state.currentAgentAuthor = author;
                    }
                    
                    // Inspect if it carries failed outcomes!
                    let isFailure = false;
                    if (data.content && data.content.parts) {
                        let func = data.content.parts.find(p => p.functionResponse);
                        if (func) {
                            let hasError = func.functionResponse.response && (func.functionResponse.response.error || func.functionResponse.response.oauth2?.error || func.functionResponse.response.status === 'ERROR');
                            let isCredentialError = false;
                            if (hasError) {
                                let textStr = JSON.stringify(func.functionResponse.response);
                                if (textStr.toLowerCase().includes('credential') || textStr.toLowerCase().includes('authenticated') || textStr.toLowerCase().includes('auth')) {
                                    isCredentialError = true;
                                }
                            }
                            if (func.functionResponse.name === 'adk_request_credential') {
                                if (hasError) isFailure = true;
                            } else if (isCredentialError) {
                                isFailure = true;
                            }
                        }
                    }

                    if (card && card.parentNode) {
                        card.remove();
                        const badge = document.createElement('div');
                        if (isFailure) {
                            badge.className = 'auth-success-card';
                            badge.style.backgroundColor = '#fee2e2';
                            badge.style.borderColor = '#f87171';
                            badge.style.color = '#b91c1c';
                            badge.innerHTML = `<i class="fas fa-exclamation-circle"></i> Authentication Failed`;
                        } else {
                            badge.className = 'auth-success-card';
                            badge.innerHTML = `<i class="fas fa-check-circle"></i> ${currentToolName} authenticated with Google`;
                        }
                        state.currentAgentMessageDiv.appendChild(badge);
                    }

                    return processStreamData(data, state.currentAgentMessageDiv, targetSessionId);
                } catch (e) {
                    console.error('Error parsing JSON from SSE:', e, 'Raw data:', trimmed);
                }
            }

            let isAuthPending = false;
            while (true) {
                const { value, done } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (trimmedLine === '') {
                            if (currentEventData) {
                                if (handleEvent(currentEventData)) {
                                    isAuthPending = true;
                                    break;
                                }
                                currentEventData = '';
                            }
                        } else if (line.startsWith('data: ')) {
                            currentEventData += line.substring(6) + '\n';
                        }
                    }
                }

                if (isAuthPending) {
                    reader.cancel();
                    activeConnections.delete(targetSessionId);
                    updateStatus('', '', targetSessionId);
                    break;
                }

                if (done) {
                    if (buffer && buffer.startsWith('data: ')) {
                        currentEventData += buffer.substring(6) + '\n';
                    }
                    if (currentEventData) {
                        handleEvent(currentEventData);
                    }
                    activeConnections.delete(targetSessionId);
                    updateStatus('', '', targetSessionId);
                    break;
                }
            }
        } catch (error) {
             console.error('Error during stream resumption:', error);
             activeConnections.delete(targetSessionId);
             updateStatus('', '', targetSessionId);
        } finally {
            state.isStreaming = false;
            state.currentReader = null;
            sendButton.classList.remove('hidden');
            stopButton.classList.add('hidden');
        }
    }

    function processStreamData(data, agentMessageDiv, targetSessionId) {
        const state = getSessionState(targetSessionId);
        let hasThought = false;
        let thoughtText = '';
        let hasContent = false;
        let contentText = '';
        let toolCall = null;
        let toolResponse = null;

        if (data.content && data.content.parts) {
            for (const part of data.content.parts) {
                if (part.thought) {
                    hasThought = true;
                    thoughtText += part.text || (typeof part.thought === 'string' ? part.thought : '');
                } else if (part.text) {
                    hasContent = true;
                    contentText += part.text;
                } else if (part.functionCall) {
                    toolCall = part.functionCall;
                } else if (part.functionResponse) {
                    toolResponse = part.functionResponse;
                }
            }
        }

        if (data.thought) {
            hasThought = true;
            thoughtText += data.thought;
        }

        const placeholder = agentMessageDiv.querySelector('.typing-indicator');
        if (placeholder && (hasThought || hasContent || toolCall || toolResponse || (data.actions && data.actions.artifactDelta))) {
             placeholder.parentElement.remove();
        }

        if (toolResponse) {
            let skip = false;
            let failedAuth = false;
            
            let hasError = toolResponse.response && (toolResponse.response.error || toolResponse.response.oauth2?.error || (toolResponse.response.status && toolResponse.response.status === 'ERROR'));
            let isCredentialError = false;
            if (hasError) {
                let textStr = JSON.stringify(toolResponse.response);
                if (textStr.toLowerCase().includes('credential') || textStr.toLowerCase().includes('authenticated') || textStr.toLowerCase().includes('auth')) {
                    isCredentialError = true;
                }
            }

            if (toolResponse.name === 'adk_request_credential') {
                if (!hasError) skip = true;
                else failedAuth = true;
            } else if (isCredentialError) {
                failedAuth = true;
            }

            if (failedAuth) {
                const state = getSessionState(targetSessionId);
                state.toolFailed = true;
                if (state.currentReader) {
                    state.currentReader.cancel();
                }
                return true;
            }

            if (!skip) {
                updateStatus('Thinking...', 'thinking', targetSessionId);
                if (state.isThinking) stopThinking(state);

                const details = document.createElement('details');
                details.classList.add('tool-call');
                if (failedAuth) details.setAttribute('open', 'true'); // Keep failed auth open!

            const summary = document.createElement('summary');
            summary.innerHTML = `<i class="fas fa-check-circle"></i> Tool Result: ${toolResponse.name}`;
            details.appendChild(summary);

            const content = document.createElement('div');
            content.classList.add('tool-content');
            content.innerHTML = `<pre><code class="language-json">${JSON.stringify(toolResponse.response, null, 2)}</code></pre>`;
            hljs.highlightElement(content.querySelector('code'));
            details.appendChild(content);

            agentMessageDiv.appendChild(details);

            state.currentBlockType = 'toolResponse';
            state.currentBlockElement = details;
            if (failedAuth) {
                state.authFailed = true;
                return true;
            }
          }
        }

        if (hasThought) {
            updateStatus('Thinking...', 'thinking', targetSessionId);

            if (thoughtText.trim() === (state.accumulatedThoughts || '').trim()) {
                // Skip creating duplicate block!
            } else {
                if (state.currentBlockType !== 'thinking') {
                    if (state.isThinking) stopThinking(state);
                    state.isThinking = true;

                    state.currentThinkingContainer = document.createElement('div');
                    state.currentThinkingContainer.classList.add('thinking-container');

                    const header = document.createElement('div');
                    header.classList.add('thinking-header');
                    header.innerHTML = `
                        <svg class="spinner" viewBox="0 0 50 50">
                            <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
                        </svg>
                        Thinking...
                    `;
                    state.currentThinkingContainer.appendChild(header);

                    const currentThinkingContent = document.createElement('div');
                    currentThinkingContent.classList.add('thinking-content');
                    state.currentThinkingContainer.appendChild(currentThinkingContent);

                    agentMessageDiv.appendChild(state.currentThinkingContainer);

                    state.currentBlockType = 'thinking';
                    state.currentBlockElement = currentThinkingContent;
                    state.accumulatedThoughts = '';
                }

                state.accumulatedThoughts += thoughtText;
                state.currentBlockElement.innerHTML = DOMPurify.sanitize(marked.parse(state.accumulatedThoughts));
                state.currentBlockElement.querySelectorAll('pre code').forEach(hljs.highlightElement);
            }
        }

        if (toolCall) {
            updateStatus('Working...', 'working', targetSessionId);
            if (state.isThinking) stopThinking(state);

            if (toolCall.name === 'adk_request_credential') {
                handleAuthRequired(toolCall, agentMessageDiv, targetSessionId);
                return true;
            } else {
                const details = document.createElement('details');
                details.classList.add('tool-call');

            const summary = document.createElement('summary');
            summary.innerHTML = `<i class="fas fa-cogs"></i> Tool Call: ${toolCall.name}`;
            details.appendChild(summary);

            const content = document.createElement('div');
            content.classList.add('tool-content');

            if (toolCall.args && toolCall.args.code) {
                const markdownCode = `\`\`\`python\n${toolCall.args.code}\n\`\`\``;
                content.innerHTML = DOMPurify.sanitize(marked.parse(markdownCode));
            } else {
                const pre = document.createElement('pre');
                const code = document.createElement('code');
                code.classList.add('language-json');
                code.textContent = JSON.stringify(toolCall.args, null, 2);
                pre.appendChild(code);
                content.appendChild(pre);
            }
            content.querySelectorAll('pre code').forEach(hljs.highlightElement);
            details.appendChild(content);

            agentMessageDiv.appendChild(details);

            state.currentBlockType = 'toolCall';
            state.currentBlockElement = details;
            }
        }

        const textToAppend = contentText || data.text;
        if (hasContent || data.text) {
            if (state.isThinking) stopThinking(state);

            if (textToAppend) {
                if (textToAppend.trim() === (state.accumulatedText || '').trim()) {
                    // Skip creating duplicate block!
                } else {
                    if (state.currentBlockType !== 'text') {
                        const newContentDiv = document.createElement('div');
                        newContentDiv.classList.add('message-content');
                        agentMessageDiv.appendChild(newContentDiv);
                        state.currentBlockType = 'text';
                        state.currentBlockElement = newContentDiv;
                        state.accumulatedText = '';
                    }
                    state.accumulatedText += textToAppend;
                    state.currentBlockElement.innerHTML = DOMPurify.sanitize(marked.parse(state.accumulatedText));
                    state.currentBlockElement.querySelectorAll('pre code').forEach(hljs.highlightElement);
                    state.currentBlockElement.setAttribute('data-raw-text', state.accumulatedText);
                }
            }
        }
        
        if (data.actions && data.actions.artifactDelta) {
            const artifactDelta = data.actions.artifactDelta;
            if (Object.keys(artifactDelta).length > 0) {
                if (state.isThinking) stopThinking(state);
                for (const [filename, version] of Object.entries(artifactDelta)) {
                    fetchArtifactContent(filename, version, agentMessageDiv);
                }
            }
        }
        return false;
    }

    async function fetchArtifactContent(filename, version, parentElement) {
        try {
            const response = await fetch(`/apps/${appName}/users/${userId}/sessions/${sessionId}/artifacts/${filename}?version=${version}`);
            if (!response.ok) {
                console.error(`Failed to fetch artifact ${filename}: ${response.statusText}`);
                return;
            }
            const part = await response.json();

            const artifact = {
                filename: filename,
                version: version
            };

            if (part.text) {
                artifact.text_content = part.text;
            } else if (part.inlineData) {
                artifact.mime_type = part.inlineData.mimeType ? part.inlineData.mimeType.trim() : '';
                artifact.base64_data = part.inlineData.data ? part.inlineData.data.replace(/\s/g, '') : '';
            } else if (part.fileData) {
                 artifact.text_content = `File Data URI: ${part.fileData.fileUri}`;
            }

            const wasAtBottom = chatContainer.scrollHeight - chatContainer.clientHeight <= chatContainer.scrollTop + 10;
            renderArtifact(artifact, parentElement);

            if (wasAtBottom) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        } catch (error) {
            console.error(`Error fetching artifact ${filename}:`, error);
        }
    }

    function appendChunk(element, text) {
        const currentText = element.getAttribute('data-raw-text') || '';
        let newText = currentText + text;

        element.setAttribute('data-raw-text', newText);
        element.innerHTML = DOMPurify.sanitize(marked.parse(newText));
        element.querySelectorAll('pre code').forEach(hljs.highlightElement);
    }

    function appendMessage(role, text, file = null, isPlaceholder = false, author = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${role}-message`);

        if (role === 'agent' && author && author !== 'agent' && author !== 'user') {
            const authorDiv = document.createElement('div');
            authorDiv.classList.add('message-author');
            authorDiv.innerHTML = `<i class="fas fa-robot"></i> ${author}`;
            messageDiv.appendChild(authorDiv);
        }

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        if (isPlaceholder) {
            contentDiv.innerHTML = '<span class="typing-indicator">...</span>';
        } else if (text) {
            contentDiv.innerHTML = DOMPurify.sanitize(marked.parse(text));
            contentDiv.setAttribute('data-raw-text', text);
            contentDiv.querySelectorAll('pre code').forEach(hljs.highlightElement);
        }

        if (file) {
            const mediaDiv = document.createElement('div');
            mediaDiv.classList.add('message-media');

            const url = URL.createObjectURL(file);
            if (file.type.startsWith('image/')) {
                const img = document.createElement('img');
                img.src = url;
                mediaDiv.appendChild(img);
            } else if (file.type.startsWith('video/')) {
                const vid = document.createElement('video');
                vid.src = url;
                vid.controls = true;
                mediaDiv.appendChild(vid);
            }
            contentDiv.appendChild(mediaDiv);
        }

        messageDiv.appendChild(contentDiv);
        messageList.appendChild(messageDiv);

        const state = getSessionState(sessionId);
        state.messageElements.push(messageDiv);

        return messageDiv;
    }

    function base64ToBlob(base64, mimeType) {
        let cleanBase64 = base64;
        const match = base64.match(/^data:.*?base64,(.*)$/);
        if (match) {
            cleanBase64 = match[1];
        }

        // Convert URL-safe base64 to standard base64
        cleanBase64 = cleanBase64.replace(/-/g, '+').replace(/_/g, '/');

        // Pad if missing
        const missingPadding = cleanBase64.length % 4;
        if (missingPadding === 2) cleanBase64 += '==';
        if (missingPadding === 3) cleanBase64 += '=';

        console.log('cleanBase64 start:', cleanBase64.substring(0, 100));
        console.log('cleanBase64 length:', cleanBase64.length);

        try {
            const byteCharacters = atob(cleanBase64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            return new Blob([byteArray], {type: mimeType});
        } catch (e) {
            console.error('atob failed on string:', cleanBase64.substring(0, 100));
            throw e;
        }
    }

    function renderArtifact(artifact, parentElement) {
        const card = document.createElement('div');
        card.classList.add('artifact-card');

        const header = document.createElement('div');
        header.classList.add('artifact-header');
        header.textContent = `Artifact: ${artifact.filename || 'File'}${artifact.version ? ` (v${artifact.version})` : ''}`;
        card.appendChild(header);

        const content = document.createElement('div');
        content.classList.add('artifact-content');

        if (artifact.mime_type && artifact.mime_type.startsWith('image/')) {
             const img = document.createElement('img');
             try {
                 const blob = base64ToBlob(artifact.base64_data, artifact.mime_type);
                 const url = URL.createObjectURL(blob);
                 img.src = url;
             } catch (e) {
                 console.error('Error creating blob from base64:', e);
                 img.src = `data:${artifact.mime_type};base64,${artifact.base64_data}`; // fallback
             }
             content.appendChild(img);
        } else if (artifact.mime_type && artifact.mime_type.startsWith('video/')) {
             const vid = document.createElement('video');
             vid.src = `data:${artifact.mime_type};base64,${artifact.base64_data}`;
             vid.controls = true;
             content.appendChild(vid);
        } else if (artifact.text_content) {
             content.innerHTML = DOMPurify.sanitize(marked.parse(artifact.text_content));
        } else {
             content.textContent = 'Unsupported artifact type.';
        }

        card.appendChild(content);
        parentElement.appendChild(card);
    }

    function fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    }
});
