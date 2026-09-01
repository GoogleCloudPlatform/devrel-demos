/**
 * state.js
 * Central Application State & Constant Declarations
 */
window.Bridge = window.Bridge || {};
        let currentHistory = [];
        const projectHistoryCache = {};
        let currentProfiles = [];
        let currentProjects = [];
        let activeChannel = 'lantern';
        const ICON_YELLOW_FOLDER = `<svg width="15" height="15" viewBox="0 0 24 24" fill="#fbc02d" style="vertical-align: -2px; margin-right: 3px; display: inline-block; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.15));"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>`;
        const ICON_CLOCK = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#5f6368" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px; margin-right: 3px; display: inline-block;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`;

