// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

const instrumentation = require('./instrumentation.js');
const edge = require('./edge.js');
const config = require('./config.js');

module.exports = {
  register: instrumentation.register,
  createBoundaryEdgeFetch: edge.createBoundaryEdgeFetch,
  withBoundaryEdgeMiddleware: edge.withBoundaryEdgeMiddleware,
  withBoundary: config.withBoundary,
  injectNextConfig: config.injectNextConfig,
};
