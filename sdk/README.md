# Bergendy SDKs

**One Rust core, two thin language wrappers.**

Bergendy implements kernel sandboxing, output compression, and the
compartment runtime once in Rust. The Python and TypeScript SDKs expose the
supported native bindings directly:

```
bergendy-core (Rust)
 |-- pyo3 module  (bergendy._core)     -> Python SDK (published on PyPI as bergendy)
 `-- napi crate   (sdk/typescript/native) -> TypeScript SDK (Node addon)
```

## Prerequisites

All SDKs require the Rust core built once (from the repository root):

```bash
cargo build --release
```

This produces `target/release/libbergendy_core.dylib`/`.so`, and the
rlib used by the napi crate.

## TypeScript SDK: `sdk/typescript/`

The package is built from this repository. Publish it only after the platform
packages have been built and uploaded at the same version:

```bash
cd sdk/typescript
npm install
npm run build   # compiles the napi addon
npm test
```

```ts
import * as bergendy from '@boundary/sdk'

bergendy.version()                    // "1.1.3"
bergendy.sandboxSupported()           // true
const out = bergendy.compress(text)

// Compartment runtime handle (parse once, route many).
const rt = new bergendy.Runtime(configs, edgesJSON)
rt.canRoute('a', 'b')        // true
rt.runOrder()                // ['a', 'b', ...]
rt.names()                   // ['a', 'b', ...]
```

## Python SDK: `python/bergendy/`

Published on PyPI as `bergendy` (with `boundary` backward compatibility): the same kernel-enforced isolation,
compartments, snapshots, and credential proxy, callable from Python 3.10+:

```bash
pip install bergendy
```

```python
from bergendy import Boundary
```

## Notes

- Native sandbox application is **irreversible** for the process lifetime.
- The TypeScript SDK's `Runtime` handle (and the Rust core's `names()`
  method) is exercised by `npm test`.
- The Rust core, Python package, TypeScript package, platform packages, and
  napi crate are kept in lockstep at `1.0.4`.
