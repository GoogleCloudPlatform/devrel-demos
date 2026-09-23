/**
 * a2a-monitor.js
 * A2A Autonomous Collaboration Play | Pause Controller & Live Monitor
 */

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

        const isProjectPaused = Boolean(
            status.global_paused ||
            (status.paused_projects && (
                status.paused_projects.includes(activeChannel) ||
                status.paused_projects.includes(normChannel) ||
                status.paused_projects.includes('proj_' + normChannel)
            )) ||
            (projObj && projObj.a2a_paused)
        );

        a2aPausedState = isProjectPaused;

        // Update Play / Pause button states
        const btnPlay = document.getElementById('btnA2APlay');
        const btnPause = document.getElementById('btnA2APause');
        if (btnPlay && btnPause) {
            if (isProjectPaused) {
                btnPause.classList.add('active', 'pause-active');
                btnPlay.classList.remove('active', 'play-active');
            } else {
                btnPlay.classList.add('active', 'play-active');
                btnPause.classList.remove('active', 'pause-active');
            }
        }

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
            } else if (status.queue_size > 0 && !isProjectPaused) {
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

async function setA2AMode(shouldPause) {
    const isProject = (activeChannel === 'lantern' || (typeof activeChannel === 'string' && activeChannel.startsWith('proj_')));
    if (!isProject) return;

    a2aPausedState = shouldPause;

    // Optimistic UI updates
    const btnPlay = document.getElementById('btnA2APlay');
    const btnPause = document.getElementById('btnA2APause');
    if (btnPlay && btnPause) {
        if (shouldPause) {
            btnPause.classList.add('active', 'pause-active');
            btnPlay.classList.remove('active', 'play-active');
        } else {
            btnPlay.classList.add('active', 'play-active');
            btnPause.classList.remove('active', 'pause-active');
        }
    }

    // Update project in currentProjects cache
    const normChannel = typeof activeChannel === 'string' ? activeChannel.replace('proj_', '') : '';
    if (typeof currentProjects !== 'undefined' && Array.isArray(currentProjects)) {
        const pObj = currentProjects.find(x => x.id === activeChannel || x.id === normChannel);
        if (pObj) {
            pObj.a2a_paused = shouldPause;
        }
    }

    // Send API request
    try {
        const endpoint = shouldPause ? '/api/a2a/pause' : '/api/a2a/resume';
        await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: activeChannel })
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
    const isPaused = Boolean(projObj && projObj.a2a_paused);
    a2aPausedState = isPaused;

    const btnPlay = document.getElementById('btnA2APlay');
    const btnPause = document.getElementById('btnA2APause');
    if (btnPlay && btnPause) {
        if (isPaused) {
            btnPause.classList.add('active', 'pause-active');
            btnPlay.classList.remove('active', 'play-active');
        } else {
            btnPlay.classList.add('active', 'play-active');
            btnPause.classList.remove('active', 'pause-active');
        }
    }

    // Poll immediately to synchronize server status
    pollA2AStatus();
}

async function toggleA2APause() {
    return setA2AMode(!a2aPausedState);
}
