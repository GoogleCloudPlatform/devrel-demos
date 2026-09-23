/**
 * a2a-monitor.js
 * A2A Autonomous Collaboration Controller & Live Monitor
 * Supports 3-Way Mode Control: [ ⏸ Pause | ▶ Mentions | 🌐 Open Floor ]
 */

let a2aModeState = 'mentions';

function renderA2AButtons(mode) {
    const btnPause = document.getElementById('btnA2APause');
    const btnMentions = document.getElementById('btnA2AMentions') || document.getElementById('btnA2APlay');
    const btnOpenFloor = document.getElementById('btnA2AOpenFloor') || document.getElementById('btnA2APulse');

    const isOpenFloor = (mode === 'open_floor' || mode === 'ambient' || mode === 'pulse');

    if (btnPause) {
        const isPaused = (mode === 'paused');
        btnPause.classList.toggle('active', isPaused);
        btnPause.classList.toggle('pause-active', isPaused);
    }
    if (btnMentions) {
        const isMentions = (mode === 'mentions');
        btnMentions.classList.toggle('active', isMentions);
        btnMentions.classList.toggle('mentions-active', isMentions);
        btnMentions.classList.toggle('play-active', isMentions);
    }
    if (btnOpenFloor) {
        btnOpenFloor.classList.toggle('active', isOpenFloor);
        btnOpenFloor.classList.toggle('open-floor-active', isOpenFloor);
        btnOpenFloor.classList.toggle('pulse-active', isOpenFloor);
    }
}

async function pollA2AStatus() {
    try {
        const res = await fetch('/api/a2a/status');
        if (!res.ok) return;
        const data = await res.json();
        const status = data.status || {};

        const prevActiveJson = JSON.stringify(latestA2AActiveTask);
        latestA2AActiveTask = status.active_task || null;
        const newActiveJson = JSON.stringify(latestA2AActiveTask);

        // If active task changed, refresh chat thread to show/hide Google Chat typing indicator
        if (prevActiveJson !== newActiveJson) {
            if (typeof renderChatThread === 'function') renderChatThread();
            if (latestA2AActiveTask && typeof scrollToBottom === 'function') scrollToBottom();
        }

        const controlGroup = document.getElementById('a2aControlGroup');
        if (!controlGroup) return;

        const isProject = (activeChannel === 'lantern' || (typeof activeChannel === 'string' && activeChannel.startsWith('proj_')));
        if (!isProject) {
            controlGroup.style.display = 'none';
            return;
        }

        controlGroup.style.display = 'inline-flex';

        const normChannel = typeof activeChannel === 'string' ? activeChannel.replace('proj_', '') : '';
        const projObj = (typeof currentProjects !== 'undefined' && Array.isArray(currentProjects))
            ? (currentProjects.find(x => x.id === activeChannel || x.id === normChannel))
            : null;

        let currentMode = 'mentions';
        if (status.global_paused) {
            currentMode = 'paused';
        } else if (status.project_modes && (
            status.project_modes[activeChannel] ||
            status.project_modes[normChannel] ||
            status.project_modes['proj_' + normChannel]
        )) {
            currentMode = status.project_modes[activeChannel] ||
                          status.project_modes[normChannel] ||
                          status.project_modes['proj_' + normChannel];
        } else if (projObj && projObj.a2a_mode) {
            currentMode = projObj.a2a_mode;
        } else if (status.paused_projects && (
            status.paused_projects.includes(activeChannel) ||
            status.paused_projects.includes(normChannel) ||
            status.paused_projects.includes('proj_' + normChannel)
        )) {
            currentMode = 'paused';
        } else if (projObj && projObj.a2a_paused) {
            currentMode = 'paused';
        }

        if (currentMode === 'ambient' || currentMode === 'pulse') {
            currentMode = 'open_floor';
        }

        a2aModeState = currentMode;
        a2aPausedState = (currentMode === 'paused');

        // Update 3-Way button states
        renderA2AButtons(currentMode);

        // Update Live working indicator
        const liveIndicator = document.getElementById('a2aLiveIndicator');
        const liveText = document.getElementById('a2aLiveText');
        if (liveIndicator && liveText) {
            const activeTask = status.active_task;
            const taskInThisRoom = activeTask && (
                activeTask.project_id === activeChannel ||
                activeTask.project_id === normChannel ||
                activeTask.project_id === ('proj_' + normChannel)
            );

            if (taskInThisRoom) {
                liveIndicator.style.display = 'inline-flex';
                liveText.innerText = `⚡ ${activeTask.sender} → ${(activeTask.target || 'AGENT').toUpperCase()}...`;
            } else if (status.queue_size > 0 && currentMode !== 'paused') {
                liveIndicator.style.display = 'inline-flex';
                liveText.innerText = `⚡ Queued (${status.queue_size})`;
            } else {
                liveIndicator.style.display = 'none';
            }
        }
    } catch (e) {
        // Silently ignore network poll glitches
    }
}

async function setA2AMode(targetMode) {
    const isProject = (activeChannel === 'lantern' || (typeof activeChannel === 'string' && activeChannel.startsWith('proj_')));
    if (!isProject) return;

    let mode = targetMode;
    if (typeof targetMode === 'boolean') {
        mode = targetMode ? 'paused' : 'mentions';
    }
    if (mode === 'ambient' || mode === 'pulse') {
        mode = 'open_floor';
    }
    if (!['paused', 'mentions', 'open_floor'].includes(mode)) {
        mode = 'mentions';
    }

    a2aModeState = mode;
    a2aPausedState = (mode === 'paused');

    // Optimistic UI updates
    renderA2AButtons(mode);

    // Update project in currentProjects cache
    const normChannel = typeof activeChannel === 'string' ? activeChannel.replace('proj_', '') : '';
    if (typeof currentProjects !== 'undefined' && Array.isArray(currentProjects)) {
        const pObj = currentProjects.find(x => x.id === activeChannel || x.id === normChannel);
        if (pObj) {
            pObj.a2a_mode = mode;
            pObj.a2a_paused = (mode === 'paused');
        }
    }

    // Send API request
    try {
        await fetch('/api/a2a/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: activeChannel, mode: mode })
        });
        pollA2AStatus();
    } catch (e) {
        console.error("Error setting A2A mode:", e);
    }
}

function updateA2AHeaderOnRoomSwitch() {
    const isProject = (activeChannel === 'lantern' || (typeof activeChannel === 'string' && activeChannel.startsWith('proj_')));
    const controlGroup = document.getElementById('a2aControlGroup');
    if (!controlGroup) return;

    if (!isProject) {
        controlGroup.style.display = 'none';
        return;
    }

    controlGroup.style.display = 'inline-flex';

    const normChannel = typeof activeChannel === 'string' ? activeChannel.replace('proj_', '') : '';
    const projObj = (typeof currentProjects !== 'undefined' && Array.isArray(currentProjects))
        ? (currentProjects.find(x => x.id === activeChannel || x.id === normChannel))
        : null;

    let currentMode = 'mentions';
    if (projObj) {
        if (projObj.a2a_mode) {
            currentMode = projObj.a2a_mode;
        } else if (projObj.a2a_paused) {
            currentMode = 'paused';
        }
    }
    if (currentMode === 'ambient' || currentMode === 'pulse') {
        currentMode = 'open_floor';
    }

    a2aModeState = currentMode;
    a2aPausedState = (currentMode === 'paused');
    renderA2AButtons(currentMode);

    // Poll immediately to synchronize server status
    pollA2AStatus();
}

async function toggleA2APause() {
    return setA2AMode(a2aPausedState ? 'mentions' : 'paused');
}
