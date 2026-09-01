/**
 * tenant-fetch.js
 * Multi-Tenancy Client Context & Header Interceptor
 * MUST be loaded first before any other module executes a network request.
 */
// Multi-Tenancy Client Context & Header Interceptor
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            const opts = Object.assign({}, options);
            opts.headers = Object.assign({}, opts.headers || {});
            if (!opts.headers['X-Bridge-Tenant-ID']) {
                const urlParams = new URLSearchParams(window.location.search);
                const tenant = urlParams.get('tenant') || localStorage.getItem('bridge_tenant_id') || 'default';
                opts.headers['X-Bridge-Tenant-ID'] = tenant;
            }
            return originalFetch(url, opts);
        };

