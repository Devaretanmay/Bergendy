// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

const http = require('http');
const https = require('https');

let originalFetch = globalThis.fetch;
let originalHttpRequest = http.request;
let originalHttpsRequest = https.request;
let isMockInstalled = false;

/**
 * Intercept outbound HTTP / fetch traffic and redirect it to the Ghost Proxy.
 * This guarantees zero external network calls in the test sandbox.
 */
function installMockProxy(proxyUrlStr) {
  if (isMockInstalled) return;
  const proxyUrl = new URL(proxyUrlStr);

  // 1. Intercept globalThis.fetch
  if (typeof globalThis.fetch === 'function') {
    originalFetch = globalThis.fetch;
    globalThis.fetch = async function boundaryMockFetch(input, init = {}) {
      let targetUrl;
      if (typeof input === 'string') {
        targetUrl = input;
      } else if (input && input.url) {
        targetUrl = input.url;
      } else {
        targetUrl = String(input);
      }

      // Check if this is already pointing to the local proxy
      const parsed = new URL(targetUrl, 'http://localhost');
      if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
        return originalFetch(input, init);
      }

      const proxyTarget = `${proxyUrl.origin}${parsed.pathname}${parsed.search}`;

      const headers = new Headers(init.headers || (typeof input === 'object' && input.headers ? input.headers : {}));
      headers.set('x-boundary-original-url', targetUrl);
      headers.set('x-boundary-mock-client', 'boundary-sdk-node');

      const modifiedInit = {
        ...init,
        headers,
      };

      return originalFetch(proxyTarget, modifiedInit);
    };
  }

  const createMockRequest = (originalReq) => {
    return function boundaryMockRequest(...args) {
      let options = {};
      let callback;

      if (typeof args[0] === 'string' || args[0] instanceof URL) {
        const parsed = new URL(args[0], 'http://localhost');
        options = {
          protocol: parsed.protocol,
          hostname: parsed.hostname,
          port: parsed.port,
          path: `${parsed.pathname}${parsed.search}`,
          headers: {},
        };
        if (typeof args[1] === 'object') {
          Object.assign(options, args[1]);
          callback = args[2];
        } else if (typeof args[1] === 'function') {
          callback = args[1];
        }
      } else if (typeof args[0] === 'object') {
        options = { ...args[0] };
        callback = args[1];
      }

      const host = options.hostname || options.host || 'localhost';
      if (host !== 'localhost' && host !== '127.0.0.1') {
        const originalTarget = `${options.protocol || 'https:'}//${host}${options.path || '/'}`;
        options.headers = options.headers || {};
        options.headers['x-boundary-original-url'] = originalTarget;
        options.hostname = proxyUrl.hostname;
        options.host = proxyUrl.host;
        options.port = proxyUrl.port;
        options.protocol = proxyUrl.protocol;

        return originalHttpRequest(options, callback);
      }

      return originalReq.apply(this, args);
    };
  };

  http.request = createMockRequest(originalHttpRequest);
  https.request = createMockRequest(originalHttpsRequest);

  isMockInstalled = true;
  console.log(`[Boundary SDK] Ghost Proxy active at ${proxyUrlStr}. All outbound network traffic intercepted.`);
}

function uninstallMockProxy() {
  if (!isMockInstalled) return;
  if (originalFetch) globalThis.fetch = originalFetch;
  http.request = originalHttpRequest;
  https.request = originalHttpsRequest;
  isMockInstalled = false;
}

/**
 * Initialize OpenTelemetry Auto-Instrumentation or Ghost Proxy based on environment.
 */
function initBoundaryInstrumentation() {
  const mockProxy = process.env.BOUNDARY_MOCK_PROXY;
  if (mockProxy) {
    installMockProxy(mockProxy);
    return;
  }

  try {
    const { NodeSDK } = require('@opentelemetry/sdk-node');
    const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
    const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
    const { FetchInstrumentation } = require('@opentelemetry/instrumentation-fetch');

    const exporter = new OTLPTraceExporter({
      url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4317/v1/traces',
    });

    const sdk = new NodeSDK({
      traceExporter: exporter,
      instrumentations: [
        new HttpInstrumentation(),
        new FetchInstrumentation(),
      ],
    });

    sdk.start();
    console.log('Boundary OpenTelemetry Auto-Instrumentation started. Exporting to localhost:4317');
  } catch (err) {
    console.warn('[Boundary SDK] OpenTelemetry packages not installed, skipping trace exporter:', err.message);
  }
}

if (process.env.BOUNDARY_MOCK_PROXY) {
  installMockProxy(process.env.BOUNDARY_MOCK_PROXY);
}

module.exports = {
  initBoundaryInstrumentation,
  installMockProxy,
  uninstallMockProxy,
  isMockProxyActive: () => isMockInstalled,
};
