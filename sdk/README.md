# Boundary SDKs

**One Rust core, two thin language wrappers.**

Boundary implements kernel sandboxing, output compression, and the
compartment runtime once in Rust. The Python and TypeScript SDKs expose the
supported native bindings directly:

```
boundary-core (Rust)
 |-- pyo3 module  (boundary._core)     -> Python SDK (published on PyPI)
 `-- napi crate   (sdk/typescript/native) -> TypeScript SDK (Node addon)
```

## Prerequisites

All SDKs require the Rust core built once (from the repository root):

```bash
cargo build --release
```

This produces `target/release/libboundary_core.dylib`/`.so`, and the
rlib used by the napi crate.

## TypeScript SDK: `sdk/typescript/`

The package is built from this repository. Publish it only after the platform
packages have been built and uploaded at the same version:

```bash
cd sdk/typescript
npm install
npm run build   # compiles the napi addon (boundary-native.<platform>-<arch>.node)
npm test
```

```ts
import * as boundary from '@boundary/sdk'

boundary.version()                    // "1.1.3"
boundary.sandboxSupported()           // true
const out = boundary.compress(text)

// Compartment runtime handle (parse once, route many).
// configs: { configs: [{ name: 'a', allow_outbound_to: ['b'] }, { name: 'b' }] }
// edgesJSON: '[['a','b']]'
const rt = new boundary.Runtime(configs, edgesJSON)
rt.canRoute('a', 'b')        // true
rt.runOrder()                // ['a', 'b', ...]
rt.names()                   // ['a', 'b', ...]
```

## Python SDK: `python/boundary/`

Published on PyPI as `boundary` : the same kernel-enforced isolation,
compartments, snapshots, and credential proxy, callable from Python 3.10+:

```bash
pip install boundary
```

```python
from boundary import Boundary
```

## Notes

- Native sandbox application is **irreversible** for the process lifetime.
- The TypeScript SDK's `Runtime` handle (and the Rust core's `names()`
  method) is exercised by `npm test`.
- The Rust core, Python package, TypeScript package, platform packages, and
  napi crate are kept in lockstep at `1.0.4`.
