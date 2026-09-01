/**
 * a2a-monitor.js
 * A2A Autonomous Cascade Live Monitor & Status Poller
 */
        async function pollA2AStatus() {
            try {
                const res = await fetch('/api/a2a/status');
                if (!res.ok) return;
                const data = await res.json();
                const status = data.status || {};
                const indicator = document.getElementById('a2aStatusIndicator');
                const statusText = document.getElementById('a2aStatusText');
                const btnToggle = document.getElementById('btnToggleA2A');

                const prevActiveJson = JSON.stringify(latestA2AActiveTask);
                latestA2AActiveTask = status.active_task || null;
                const newActiveJson = JSON.stringify(latestA2AActiveTask);

                // If active task changed, refresh chat thread to show/hide Google Chat typing indicator
                if (prevActiveJson !== newActiveJson) {
                    renderChatThread();
                    if (latestA2AActiveTask) scrollToBottom();
                }

                if (!indicator) return;

                const isProjectPaused = status.global_paused || (status.paused_projects && status.paused_projects.includes(activeChannel));
                a2aPausedState = isProjectPaused;

                if (status.active_task) {
                    indicator.style.display = 'inline-flex';
                    indicator.style.background = '#e8f0fe';
                    indicator.style.color = '#0b57d0';
                    statusText.innerText = `⚡ ${status.active_task.sender} → ${status.active_task.target.toUpperCase()}...`;
                    btnToggle.innerText = '⏸️';
                    btnToggle.title = 'Pause Autonomous Collaboration';
                } else if (status.queue_size > 0) {
                    indicator.style.display = 'inline-flex';
                    indicator.style.background = '#e8f0fe';
                    indicator.style.color = '#0b57d0';
                    statusText.innerText = `⚡ Queued (${status.queue_size})`;
                    btnToggle.innerText = '⏸️';
                } else if (isProjectPaused) {
                    indicator.style.display = 'inline-flex';
                    indicator.style.background = '#fef7e0';
                    indicator.style.color = '#b06000';
                    statusText.innerText = `⏸️ A2A Paused`;
                    btnToggle.innerText = '▶️';
                    btnToggle.title = 'Resume Autonomous Collaboration';
                } else {
                    indicator.style.display = 'none';
                }
            } catch (e) {
                // Silently ignore network poll glitches
            }
        }

        async function toggleA2APause() {
            try {
                const endpoint = a2aPausedState ? '/api/a2a/resume' : '/api/a2a/pause';
                await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_id: activeChannel })
                });
                pollA2AStatus();
            } catch (e) {
                console.error("Error toggling A2A state:", e);
            }
        }

