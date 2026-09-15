import assert from 'node:assert/strict';
import http from 'node:http';
import instrument from '../instrument.js';
const { installMockProxy, uninstallMockProxy, isMockProxyActive } = instrument;

// 1. Create a dummy local server representing Rust Ghost Proxy
let receivedRequests = [];
const mockServer = http.createServer((req, res) => {
  receivedRequests.push({
    method: req.method,
    url: req.url,
    headers: req.headers,
  });

  if (req.url === '/v1/payment_intents') {
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'x-boundary-mock-hit': 'true',
    });
    res.end(JSON.stringify({ id: 'pi_test_123', status: 'succeeded' }));
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'unmocked' }));
  }
});

await new Promise((resolve) => mockServer.listen(0, '127.0.0.1', resolve));
const port = mockServer.address().port;
const proxyUrl = `http://127.0.0.1:${port}`;

try {
  // 2. Install mock proxy
  installMockProxy(proxyUrl);
  assert.equal(isMockProxyActive(), true, 'Mock proxy should be active');

  // 3. Test globalThis.fetch interception
  const targetExternalUrl = 'https://api.stripe.com/v1/payment_intents';
  const resp = await fetch(targetExternalUrl, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer sk_test_fake' },
  });

  assert.equal(resp.status, 200, 'Mock response should return 200');
  const data = await resp.json();
  assert.equal(data.id, 'pi_test_123');

  assert.equal(receivedRequests.length, 1);
  const lastReq = receivedRequests[0];
  assert.equal(lastReq.url, '/v1/payment_intents', 'URL pathname should be preserved');
  assert.equal(lastReq.headers['x-boundary-original-url'], targetExternalUrl, 'Original URL should be in header');
  assert.equal(lastReq.headers['x-boundary-mock-client'], 'boundary-sdk-node');

  console.log('[PASS] SDK Ghost Proxy interception test passed: globalThis.fetch successfully routed to mock server!');
} finally {
  uninstallMockProxy();
  await new Promise((resolve) => mockServer.close(resolve));
}
