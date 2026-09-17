# Gates: Bergendy Hybrid Architecture (AST + AI)

Scope: Build the hybrid architecture combining deterministic AST analysis/verification with AI schema generation and code transformation.

- [x] G1: Context extractor implemented in Rust and exposed via PyO3
  CHECK: .venv/bin/python -c "import bergendy._core as c; assert hasattr(c, 'extract_precise_context'); print('G1_PASS')"
  EXPECT: G1_PASS
  EVIDENCE: Output: G1_PASS (exit 0)

- [x] G2: AST verifier with 6 verification checks implemented in Rust and exposed via PyO3
  CHECK: .venv/bin/python -c "import bergendy._core as c; assert hasattr(c, 'ast_verify'); print('G2_PASS')"
  EXPECT: G2_PASS
  EVIDENCE: Output: G2_PASS (exit 0)

- [x] G3: Structured transformation prompt template created
  CHECK: test -f python/bergendy/prompts/transformation.txt && echo "G3_PASS"
  EXPECT: G3_PASS
  EVIDENCE: Output: G3_PASS (exit 0)

- [x] G4: AI generation + AST verification retry loop implemented in python/bergendy/hunt.py
  CHECK: .venv/bin/python -c "from bergendy.hunt import ai_generate_patch; print('G4_PASS')"
  EXPECT: G4_PASS
  EVIDENCE: Output: G4_PASS (exit 0)

- [x] G5: Native Rust unit tests pass (129 tests including new context extractor & AST verifier tests)
  CHECK: cargo test --lib
  EXPECT: test result: ok. 129 passed; 0 failed
  EVIDENCE: test result: ok. 129 passed; 0 failed; 0 ignored; finished in 0.05s (exit 0)

- [x] G6: Complete test suite passes (Ruff lint + Rust tests + Python test suite)
  CHECK: .venv/bin/python scripts/run_all_tests.py
  EXPECT: ALL CODEBASE HYGIENE CHECKS & TEST SUITES PASSED
  EVIDENCE: Ruff clean, 129 Rust tests passed, 481 Python tests passed (exit 0)

- [x] G7: End-to-end verification of bergendy fix on real Next.js/Stripe application
  CHECK: cd /tmp/bergendy_fix_test && bergendy see
  EXPECT: BERGENDY RUNTIME: score 100/100
  EVIDENCE: BERGENDY RUNTIME: score 100/100 (A — shielded), 0 unvalidated call(s) in 3 files (exit 0)
