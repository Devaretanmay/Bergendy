import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

import {
  withBoundary,
  injectNextConfig,
  register,
  createBoundaryEdgeFetch,
} from '../dist/index.mjs';

console.log('--- Testing Next.js Boundary Integration ---');

// 1. Test withBoundary config wrapper
const rawConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: true,
  },
};
const wrapped = withBoundary(rawConfig);
assert.equal(wrapped.experimental.instrumentationHook, true);
console.log('[PASS] withBoundary config wrapper successfully enables instrumentationHook: true');

// 2. Test injectNextConfig automated setup
const tmpAppDir = fs.mkdtempSync(path.join(os.tmpdir(), 'boundary-next-test-'));
try {
  fs.writeFileSync(
    path.join(tmpAppDir, 'package.json'),
    JSON.stringify({ name: 'my-next-app', dependencies: { next: '^15.0.0', react: '^19.0.0' } }),
    'utf8'
  );
  fs.writeFileSync(
    path.join(tmpAppDir, 'next.config.mjs'),
    `const nextConfig = {\n  reactStrictMode: true,\n};\nexport default nextConfig;\n`,
    'utf8'
  );

  const injectRes = injectNextConfig(tmpAppDir);
  assert.equal(injectRes.detected, true, 'Next.js should be detected');
  assert.equal(injectRes.instrumentationCreated, true, 'instrumentation.ts should be created');
  assert.equal(injectRes.configUpdated, true, 'next.config.mjs should be updated');

  const updatedConfig = fs.readFileSync(path.join(tmpAppDir, 'next.config.mjs'), 'utf8');
  assert.ok(updatedConfig.includes('instrumentationHook: true'), 'Config should include instrumentationHook');

  const instContent = fs.readFileSync(path.join(tmpAppDir, 'instrumentation.ts'), 'utf8');
  assert.ok(instContent.includes('@boundary/nextjs/instrumentation'), 'Instrumentation should import @boundary/nextjs');
  console.log('[PASS] injectNextConfig successfully detected repo, created instrumentation.ts, and updated next.config.mjs');
} finally {
  fs.rmSync(tmpAppDir, { recursive: true, force: true });
}

// 3. Test Edge Runtime non-blocking fetch telemetry
let collectedSpans = [];
const mockCollector = http.createServer((req, res) => {
  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    try {
      const json = JSON.parse(body);
      collectedSpans.push(json);
    } catch {}
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ partialSuccess: {} }));
  });
});

await new Promise(resolve => mockCollector.listen(0, '127.0.0.1', resolve));
const collectorPort = mockCollector.address().port;
const collectorUrl = `http://127.0.0.1:${collectorPort}/v1/traces`;

// Mock target external API (e.g. Stripe)
const mockStripe = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ id: 'pi_next_edge_123', amount: 9900 }));
});
await new Promise(resolve => mockStripe.listen(0, '127.0.0.1', resolve));
const stripePort = mockStripe.address().port;

try {
  const edgeFetch = createBoundaryEdgeFetch({ collectorUrl });
  const resp = await edgeFetch(`http://127.0.0.1:${stripePort}/v1/payment_intents`, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer sk_test' },
  });

  assert.equal(resp.status, 200);
  const data = await resp.json();
  assert.equal(data.id, 'pi_next_edge_123');

  await new Promise(r => setTimeout(r, 100));

  assert.ok(collectedSpans.length > 0, 'Collector should receive OTLP trace from Edge runtime');
  const span = collectedSpans[0].resourceSpans[0].scopeSpans[0].spans[0];
  const bodyAttr = span.attributes.find(a => a.key === 'http.response.body');
  assert.ok(bodyAttr && bodyAttr.value.stringValue.includes('pi_next_edge_123'), 'Span should contain response body');

  console.log('[PASS] Edge Runtime createBoundaryEdgeFetch successfully captured response body and exported OTLP trace');
} finally {
  await new Promise(r => mockCollector.close(r));
  await new Promise(r => mockStripe.close(r));
}

const ghostServer = http.createServer((req, res) => {
  if (req.url === '/v1/customers') {
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'x-boundary-mock-hit': 'true',
    });
    res.end(JSON.stringify({ id: 'cus_ghost_nextjs', name: 'YC Founder' }));
  } else {
    res.writeHead(404);
    res.end();
  }
});
await new Promise(r => ghostServer.listen(0, '127.0.0.1', r));
const ghostPort = ghostServer.address().port;

try {
  process.env.BOUNDARY_MOCK_PROXY = `http://127.0.0.1:${ghostPort}`;
  const edgeFetchMock = createBoundaryEdgeFetch();

  const mockResp = await edgeFetchMock('https://api.stripe.com/v1/customers', {
    method: 'GET',
  });

  assert.equal(mockResp.status, 200);
  assert.equal(mockResp.headers.get('x-boundary-mock-hit'), 'true');
  const cus = await mockResp.json();
  assert.equal(cus.id, 'cus_ghost_nextjs');

  console.log('[PASS] Next.js Ghost Proxy interception successfully verified in Edge / serverless environment!');
} finally {
  delete process.env.BOUNDARY_MOCK_PROXY;
  await new Promise(r => ghostServer.close(r));
}

console.log('All Next.js Telemetry & Edge Tests Passed!');
