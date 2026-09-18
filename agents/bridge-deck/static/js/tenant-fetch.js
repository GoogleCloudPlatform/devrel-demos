/**
 * tenant-fetch.js
 * Multi-Tenancy & Application Auth Client Context & Header Interceptor
 * MUST be loaded first before any other module executes a network request.
 */
(() => {
    // 1. Capture token from URL query params if present and persist in localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    if (urlToken) {
        try {
            localStorage.setItem('bridge_auth_token', urlToken);
            // Cleanly strip token parameter from URL without triggering a page reload
            const cleanUrl = new URL(window.location.href);
            cleanUrl.searchParams.delete('token');
            window.history.replaceState({}, document.title, cleanUrl.pathname + (cleanUrl.search ? cleanUrl.search : ''));
        } catch (e) {
            console.warn("Could not persist bridge_auth_token to localStorage:", e);
        }
    }

    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        const opts = Object.assign({}, options);
        opts.headers = Object.assign({}, opts.headers || {});
        opts.credentials = opts.credentials || 'same-origin';

        // Attach X-Bridge-Auth header if token is in localStorage or URL
        const token = urlToken || localStorage.getItem('bridge_auth_token');
        if (token && !opts.headers['X-Bridge-Auth']) {
            opts.headers['X-Bridge-Auth'] = token;
        }

        // Attach tenant scoping header
        if (!opts.headers['X-Bridge-Tenant-ID']) {
            const tenant = urlParams.get('tenant') || localStorage.getItem('bridge_tenant_id') || 'default';
            opts.headers['X-Bridge-Tenant-ID'] = tenant;
        }
        return originalFetch(url, opts);
    };
})();

