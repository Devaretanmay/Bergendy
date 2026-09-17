# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import MagicMock

import bergendy._core as _core
from bergendy.hunt import ai_generate_patch, repair_unvalidated_boundary


def test_core_extract_precise_context():
    source = """import { db } from './db';

export async function fetchStripeCharge(chargeId: string) {
  const url = `https://api.stripe.com/v1/charges/${chargeId}`;
  const res = await fetch(url, { headers: { Authorization: "Bearer sk_test" } });
  const data = await res.json();
  return data.amount;
}
"""
    samples = [{"amount": 5000, "currency": "usd", "id": "ch_123"}]
    ctx_raw = _core.extract_precise_context(
        source,
        "src/api/charges.ts",
        4,
        "https://api.stripe.com/v1/charges",
        json.dumps(samples),
        "typescript",
    )
    ctx = json.loads(ctx_raw)
    assert ctx["file"] == "src/api/charges.ts"
    assert ctx["validation_library"] == "zod"
    assert "fetchStripeCharge" in ctx["function_signature"]
    assert "await fetch(url" in ctx["enclosing_function_code"]
    assert len(ctx["data_flow"]) >= 1
    assert ctx["traffic_sample_count"] == 1


def test_core_ast_verify_balanced_syntax():
    orig_fn = "export async function getCharge() { return await fetch('https://api.stripe.com'); }"
    # Invalid syntax: unclosed brace
    patch_fn = "export async function getCharge() { return await fetch('https://api.stripe.com');"
    schema = "import { z } from 'zod';\nexport const ChargeSchema = z.object({});"
    imp = "import { ChargeSchema } from './schemas/charge';"
    ctx = json.dumps({"validation_library": "zod", "file": "test.ts"})

    ver_raw = _core.ast_verify(orig_fn, patch_fn, schema, imp, ctx)
    ver = json.loads(ver_raw)
    assert ver["syntactically_valid"] is False
    assert any("unbalanced" in err.lower() for err in ver["error_messages"])


def test_core_ast_verify_no_silent_catch():
    orig_fn = "export async function getCharge() { return await fetch('https://api.stripe.com'); }"
    # Swallowing error
    patch_fn = """export async function getCharge() {
  try {
    const res = await fetch('https://api.stripe.com');
    return ChargeSchema.parse(await res.json());
  } catch (err) {
    // silently swallowed
  }
}"""
    schema = "import { z } from 'zod';\nexport const ChargeSchema = z.object({});"
    imp = "import { ChargeSchema } from './schemas/charge';"
    ctx = json.dumps({"validation_library": "zod", "file": "test.ts"})

    ver_raw = _core.ast_verify(orig_fn, patch_fn, schema, imp, ctx)
    ver = json.loads(ver_raw)
    assert ver["no_silent_catch"] is False
    assert any("No-Swallow" in err or "silently" in err for err in ver["error_messages"])


def test_core_ast_verify_schema_wiring():
    orig_fn = "export async function getCharge() { return await fetch('https://api.stripe.com'); }"
    # Schema not wired in
    patch_fn = "export async function getCharge() { return await fetch('https://api.stripe.com'); }"
    schema = "import { z } from 'zod';\nexport const ChargeSchema = z.object({});"
    imp = "import { ChargeSchema } from './schemas/charge';"
    ctx = json.dumps({"validation_library": "zod", "file": "test.ts"})

    ver_raw = _core.ast_verify(orig_fn, patch_fn, schema, imp, ctx)
    ver = json.loads(ver_raw)
    assert ver["schema_wired"] is False
    assert any("not wired" in err for err in ver["error_messages"])


def test_core_ast_verify_valid_patch():
    orig_fn = "export async function getCharge() { const res = await fetch('https://api.stripe.com'); return await res.json(); }"
    patch_fn = """export async function getCharge() {
  const res = await fetch('https://api.stripe.com');
  return ChargeSchema.parse(await res.json());
}"""
    schema = "import { z } from 'zod';\nexport const ChargeSchema = z.object({ id: z.string() });"
    imp = "import { ChargeSchema } from './schemas/charge';"
    ctx = json.dumps({"validation_library": "zod", "file": "test.ts"})

    ver_raw = _core.ast_verify(orig_fn, patch_fn, schema, imp, ctx)
    ver = json.loads(ver_raw)
    assert ver["syntactically_valid"] is True
    assert ver["schema_wired"] is True
    assert ver["no_silent_catch"] is True
    assert ver["blast_radius_clean"] is True
    assert ver["imports_correct"] is True
    assert ver["naming_valid"] is True
    assert len(ver["error_messages"]) == 0


def test_ai_generate_patch_retry_on_verification_failure():
    # Setup mock client: first call returns silent catch, second returns valid patch
    first_response = MagicMock()
    first_response.content = """
```schema
import { z } from "zod";
export const PaymentSchema = z.object({ id: z.string() });
```

```patch
export async function pay() {
  try {
    const res = await fetch('/pay');
    return PaymentSchema.parse(await res.json());
  } catch (e) {
  }
}
```

```import
import { PaymentSchema } from './schemas/payment';
```
"""
    second_response = MagicMock()
    second_response.content = """
```schema
import { z } from "zod";
export const PaymentSchema = z.object({ id: z.string() });
```

```patch
export async function pay() {
  const res = await fetch('/pay');
  return PaymentSchema.parse(await res.json());
}
```

```import
import { PaymentSchema } from './schemas/payment';
```
"""
    mock_client = MagicMock()
    mock_client.complete.side_effect = [first_response, second_response]

    context_dict = {
        "file": "src/pay.ts",
        "language": "typescript",
        "validation_library": "zod",
        "function_signature": "export async function pay()",
        "enclosing_function_code": "export async function pay() { const res = await fetch('/pay'); return await res.json(); }",
        "line": 1,
        "column": 1,
        "callsite_code": "fetch('/pay')",
        "data_flow": [],
        "error_handling": {"type": "None"},
        "existing_imports": [],
        "traffic_samples": [{"id": "pi_123"}],
        "traffic_sample_count": 1,
    }

    result = ai_generate_patch(context_dict, mock_client, max_retries=3)
    assert result is not None
    assert result["verification"]["syntactically_valid"] is True
    assert result["verification"]["no_silent_catch"] is True
    assert "PaymentSchema.parse" in result["patch"]
    # Verified that it called complete twice (first failed, second passed)
    assert mock_client.complete.call_count == 2
    # Verify feedback was passed in the second prompt
    second_call_prompt = mock_client.complete.call_args_list[1][1]["messages"][0]["content"]
    assert "PREVIOUS ATTEMPT FAILED AST VERIFICATION" in second_call_prompt


def test_repair_unvalidated_boundary_hybrid_flow(tmp_path):
    # Setup test workspace
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    callsite = src_dir / "api.ts"
    callsite.write_text(
        "export async function getPayment(id: string) {\n"
        "  const res = await fetch(`https://api.stripe.com/v1/payments/${id}`);\n"
        "  return await res.json();\n"
        "}\n"
    )
    knowledge_dir = tmp_path / ".boundary" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    exchange_file = knowledge_dir / "exchanges.jsonl"
    exchange_file.write_text(
        json.dumps({
            "request_url": "https://api.stripe.com/v1/payments/pi_123",
            "request_path": "/v1/payments/pi_123",
            "status_code": 200,
            "response_body": {"id": "pi_123", "amount": 2000, "status": "succeeded"},
        }) + "\n"
    )

    mock_client = MagicMock()
    mock_client.complete.return_value = MagicMock(content="""
```schema
import { z } from "zod";
export const StripePaymentSchema = z.object({
  id: z.string(),
  amount: z.number().int(),
  status: z.string(),
});
export type StripePayment = z.infer<typeof StripePaymentSchema>;
```

```patch
export async function getPayment(id: string) {
  const res = await fetch(`https://api.stripe.com/v1/payments/${id}`);
  return StripePaymentSchema.parse(await res.json());
}
```

```import
import { StripePaymentSchema } from './schemas/stripe_payment';
```
""")

    res = repair_unvalidated_boundary(
        repo_dir=str(tmp_path),
        endpoint="https://api.stripe.com/v1/payments",
        callsite_file=str(callsite),
        schema_name="StripePaymentSchema",
        client=mock_client,
    )

    assert res["success"] is True
    patched_code = callsite.read_text()
    assert "StripePaymentSchema.parse" in patched_code
    assert "import { StripePaymentSchema }" in patched_code
