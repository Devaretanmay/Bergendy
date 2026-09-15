// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

const http = require('http');

let isRegistered = false;

/**
 * Next.js instrumentation register() hook.
 * Invoked once per Next.js server boot.
 */
async function register() {
  if (isRegistered) return;
  isRegistered = true;

  const runtime = process.env.NEXT_RUNTIME;

  // 1. Ghost Proxy check: If in sandbox / contract testing mode, redirect all fetch traffic
  const mockProxy = process.env.BOUNDARY_MOCK_PROXY;
  if (mockProxy) {
    installNextjsMockProxy(mockProxy);
    console.log(`[Boundary Next.js] Ghost Proxy active (${mockProxy}). Server fetch traffic intercepted.`);
    return;
  }

  // 2. Node.js server runtime: telemetry capture with cloned response extraction
  if (!runtime || runtime === 'nodejs') {
    initNextjsNodeTelemetry();
  }
}

/**
 * Intercept globalThis.fetch in Next.js Node runtime for Ghost Proxy mocking.
 */
function installNextjsMockProxy(proxyUrlStr) {
  const proxyUrl = new URL(proxyUrlStr);
  const originalFetch = globalThis.fetch;

  if (typeof originalFetch === 'function') {
    globalThis.fetch = async function boundaryNextjsMockFetch(input, init = {}) {
      let targetUrl = typeof input === 'string' ? input : (input?.url ? input.url : String(input));
      const parsed = new URL(targetUrl, 'http://localhost');

      if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
        return originalFetch(input, init);
      }

      const proxyTarget = `${proxyUrl.origin}${parsed.pathname}${parsed.search}`;
      const headers = new Headers(init.headers || (typeof input === 'object' && input.headers ? input.headers : {}));
      headers.set('x-boundary-original-url', targetUrl);
      headers.set('x-boundary-mock-client', 'boundary-nextjs');

      return originalFetch(proxyTarget, {
        ...init,
        headers,
      });
    };
  }
}

/**
 * Capture full telemetry including response JSON body in Next.js Node runtime.
 */
function initNextjsNodeTelemetry() {
  const collectorEndpoint = process.env.BOUNDARY_COLLECTOR_URL || 'http://localhost:4317/v1/traces';
  const originalFetch = globalThis.fetch;

  if (typeof originalFetch !== 'function') return;

  globalThis.fetch = async function boundaryNextjsTelemetryFetch(input, init = {}) {
    let targetUrl = typeof input === 'string' ? input : (input?.url ? input.url : String(input));
    const method = (init.method || (input && input.method) || 'GET').toUpperCase();
    const startTime = Date.now();

    let response;
    let error;

    try {
      response = await originalFetch(input, init);
      return response;
    } catch (err) {
      error = err;
      throw err;
    } finally {
      try {
        const parsed = new URL(targetUrl, 'http://localhost');
        const collectorParsed = new URL(collectorEndpoint, 'http://localhost');
        const isCollectorCall = parsed.host === collectorParsed.host;

        if (!isCollectorCall) {
          let responseBodyText = '';
          if (response) {
            try {
              const cloned = response.clone();
              responseBodyText = await cloned.text();
            } catch {
            }
          }

          const spanPayload = {
            resourceSpans: [
              {
                resource: {
                  attributes: [
                    { key: 'service.name', value: { stringValue: 'boundary-nextjs-app' } },
                  ],
                },
                scopeSpans: [
                  {
                    scope: { name: 'boundary.nextjs.fetch' },
                    spans: [
                      {
                        name: `${method} ${parsed.pathname}`,
                        kind: 3, // CLIENT
                        startTimeUnixNano: startTime * 1000000,
                        endTimeUnixNano: Date.now() * 1000000,
                        attributes: [
                          { key: 'http.method', value: { stringValue: method } },
                          { key: 'http.url', value: { stringValue: targetUrl } },
                          { key: 'http.target', value: { stringValue: `${parsed.pathname}${parsed.search}` } },
                          { key: 'http.status_code', value: { intValue: response ? response.status : (error ? 500 : 0) } },
                          { key: 'http.response.body', value: { stringValue: responseBodyText } },
                          { key: 'boundary.runtime', value: { stringValue: 'nextjs-nodejs' } },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          };

          fetch(collectorEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(spanPayload),
          }).catch(() => {});
        }
      } catch {
      }
    }
  };

  console.log('[Boundary Next.js] Node.js runtime telemetry active. Exporting to localhost:4317');
}

module.exports = {
  register,
};
