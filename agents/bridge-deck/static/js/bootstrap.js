/**
 * bootstrap.js
 * Application Initialization & Lifecycle Timers
 */
        async function initApp() {
            await fetchProjects();
            await fetchProfiles();
            await fetchEngines();
            restoreActiveChannelFromUrlOrStorage();
            setInterval(fetchHistory, 2500);
            setInterval(pollA2AStatus, 2500);
        }

        initApp();
