// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

/**
 * Next.js Edge Runtime Telemetry & Mocking
 * Specially designed for V8 isolates without Node.js async_hooks or OS sockets.
 */

/**
 * Lightweight Edge fetch wrapper that emits OTLP traces without blocking V8 isolates.
 */
function createBoundaryEdgeFetch(options = {}) {
  const collectorEndpoint = options.collectorUrl || process.env.BOUNDARY_COLLECTOR_URL || 'http://localhost:4317/v1/traces';
  const mockProxy = process.env.BOUNDARY_MOCK_PROXY;

  return async function boundaryEdgeFetch(input, init = {}) {
    let targetUrl = typeof input === 'string' ? input : (input?.url ? input.url : String(input));
    const parsed = new URL(targetUrl, 'http://localhost');
    const method = (init.method || (input && input.method) || 'GET').toUpperCase();

    // 1. If Ghost Proxy is active in sandbox, redirect to mock proxy
    if (mockProxy) {
      const proxyUrl = new URL(mockProxy);
      if (parsed.hostname !== 'localhost' && parsed.hostname !== '127.0.0.1') {
        const proxyTarget = `${proxyUrl.origin}${parsed.pathname}${parsed.search}`;
        const headers = new Headers(init.headers || (typeof input === 'object' && input.headers ? input.headers : {}));
        headers.set('x-boundary-original-url', targetUrl);
        headers.set('x-boundary-mock-client', 'boundary-nextjs-edge');

        return fetch(proxyTarget, {
          ...init,
          headers,
        });
      }
    }

    const startTime = Date.now();
    let response;
    let error;

    try {
      response = await fetch(input, init);
      return response;
    } catch (err) {
      error = err;
      throw err;
    } finally {
      const collectorParsed = new URL(collectorEndpoint, 'http://localhost');
      const isCollectorCall = parsed.host === collectorParsed.host;

      if (!isCollectorCall) {
        let responseBodyText = '';
        if (response) {
          try {
            const cloned = response.clone();
            const text = await cloned.text();
            responseBodyText = text.slice(0, 8192);
          } catch {
          }
        }

        const spanPayload = {
          resourceSpans: [
            {
              resource: {
                attributes: [
                  { key: 'service.name', value: { stringValue: 'boundary-nextjs-edge' } },
                ],
              },
              scopeSpans: [
                {
                  scope: { name: 'boundary.edge.fetch' },
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
                        { key: 'boundary.runtime', value: { stringValue: 'nextjs-edge' } },
                      ],
                    },
                  ],
                },
              ],
            },
          ],
        };

        const tracePromise = fetch(collectorEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(spanPayload),
        }).catch(() => {});

        if (options.waitUntil && typeof options.waitUntil === 'function') {
          options.waitUntil(tracePromise);
        }
      }
    }
  };
}

/**
 * Middleware wrapper for Next.js middleware.ts in Edge runtime.
 */
function withBoundaryEdgeMiddleware(middleware) {
  return async function boundaryWrappedMiddleware(request, event) {
    const edgeFetch = createBoundaryEdgeFetch({
      waitUntil: event?.waitUntil ? (p) => event.waitUntil(p) : undefined,
    });

    const prevFetch = globalThis.fetch;
    globalThis.fetch = edgeFetch;
    try {
      return await middleware(request, event);
    } finally {
      globalThis.fetch = prevFetch;
    }
  };
}

module.exports = {
  createBoundaryEdgeFetch,
  withBoundaryEdgeMiddleware,
};
