// Copyright 2026 Bergendy Authors
// SPDX-License-Identifier: Apache-2.0

use regex::Regex;
use serde::{Deserialize, Serialize};

use super::context_extractor::PreciseContext;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    pub syntactically_valid: bool,
    pub schema_wired: bool,
    pub no_silent_catch: bool,
    pub blast_radius_clean: bool,
    pub imports_correct: bool,
    pub naming_valid: bool,
    pub error_messages: Vec<String>,
}

impl VerificationResult {
    pub fn is_valid(&self) -> bool {
        self.syntactically_valid
            && self.schema_wired
            && self.no_silent_catch
            && self.blast_radius_clean
            && self.imports_correct
            && self.naming_valid
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

/// Runs the 6 deterministic AST verification checks against an AI-generated patch.
pub fn ast_verify(
    original_function: &str,
    ai_patch: &str,
    ai_schema: &str,
    import_stmt: &str,
    context: &PreciseContext,
) -> VerificationResult {
    let mut result = VerificationResult {
        syntactically_valid: false,
        schema_wired: false,
        no_silent_catch: false,
        blast_radius_clean: false,
        imports_correct: false,
        naming_valid: false,
        error_messages: Vec::new(),
    };

    // CHECK 1: Syntactic validity (balanced braces, parentheses, quotes)
    if check_syntax_balance(ai_patch) {
        result.syntactically_valid = true;
    } else {
        result.error_messages.push("Patch has unbalanced braces or parentheses.".to_string());
    }

    // CHECK 2: Schema wired into data flow
    let wired = check_schema_wired(ai_patch, &context.validation_library);
    if wired {
        result.schema_wired = true;
    } else {
        result.error_messages.push("Schema validation (.parse() or model_validate()) is not wired into the response data flow.".to_string());
    }

    // CHECK 3: No silent catch (No-Swallow Rule)
    let has_silent = detect_silent_catch(ai_patch);
    if !has_silent {
        result.no_silent_catch = true;
    } else {
        result.error_messages.push("Patch violates No-Swallow Rule: caught validation error silently without re-throwing or bubbling.".to_string());
    }

    // CHECK 4: Blast radius clean (preserves function signature and does not corrupt outer lines)
    let blast_clean = check_blast_radius(original_function, ai_patch, context);
    if blast_clean {
        result.blast_radius_clean = true;
    } else {
        result.error_messages.push("Patch modified lines outside the enclosing function or corrupted the function signature.".to_string());
    }

    // CHECK 5: Imports correct
    let import_valid = check_import_statement(import_stmt, context);
    if import_valid {
        result.imports_correct = true;
    } else {
        result.error_messages.push("Import statement is invalid, missing schema name, or malformed.".to_string());
    }

    // CHECK 6: Naming valid
    let name_valid = check_schema_naming(ai_schema, import_stmt);
    if name_valid {
        result.naming_valid = true;
    } else {
        result.error_messages.push("Schema naming convention violated: must use PascalCase ending in 'Schema' without raw URL artifacts.".to_string());
    }

    result
}

fn check_syntax_balance(code: &str) -> bool {
    let mut braces: i32 = 0;
    let mut parens: i32 = 0;
    let mut brackets: i32 = 0;
    let mut in_single_quote = false;
    let mut in_double_quote = false;
    let mut in_backtick = false;
    let mut escaped = false;

    for ch in code.chars() {
        if escaped {
            escaped = false;
            continue;
        }
        if ch == '\\' {
            escaped = true;
            continue;
        }

        if in_single_quote {
            if ch == '\'' {
                in_single_quote = false;
            }
            continue;
        }
        if in_double_quote {
            if ch == '"' {
                in_double_quote = false;
            }
            continue;
        }
        if in_backtick {
            if ch == '`' {
                in_backtick = false;
            }
            continue;
        }

        match ch {
            '\'' => in_single_quote = true,
            '"' => in_double_quote = true,
            '`' => in_backtick = true,
            '{' => braces += 1,
            '}' => braces -= 1,
            '(' => parens += 1,
            ')' => parens -= 1,
            '[' => brackets += 1,
            ']' => brackets -= 1,
            _ => {}
        }

        if braces < 0 || parens < 0 || brackets < 0 {
            return false;
        }
    }

    braces == 0 && parens == 0 && brackets == 0 && !in_single_quote && !in_double_quote && !in_backtick
}

fn check_schema_wired(patch: &str, val_lib: &str) -> bool {
    if val_lib == "pydantic" {
        patch.contains(".model_validate(")
            || patch.contains(".parse_obj(")
            || patch.contains("(") && patch.contains("Schema(")
    } else if val_lib == "struct" {
        patch.contains("json.Unmarshal(") || patch.contains(".Decode(")
    } else {
        // Zod
        patch.contains(".parse(") || patch.contains(".safeParse(")
    }
}

fn detect_silent_catch(patch: &str) -> bool {
    // Strip single-line and multi-line comments for accurate catch block body analysis
    let comment_re = Regex::new(r#"//[^\n]*|/\*[\s\S]*?\*/"#).unwrap();
    let stripped = comment_re.replace_all(patch, "");

    // Detect empty or swallowing catch/except blocks
    let silent_ts = Regex::new(r#"catch\s*(?:\([^)]*\))?\s*\{\s*(?:return\s+(?:null|undefined|false|0|\{\}|\[\])?;?\s*|;?\s*)\}"#).unwrap();
    let silent_py = Regex::new(r#"(?m)^\s*except(?:\s+[a-zA-Z0-9_]+)?:\s*(?:pass|return\s+(?:None|False|\{\}|\[\])?)\s*$"#).unwrap();

    silent_ts.is_match(&stripped) || silent_py.is_match(&stripped)
}

fn check_blast_radius(original: &str, patch: &str, context: &PreciseContext) -> bool {
    if patch.trim().is_empty() {
        return false;
    }

    // Function signature must be preserved in patch
    let sig_clean = context.function_signature.trim();
    if !sig_clean.is_empty() && !sig_clean.starts_with("anonymous") {
        let first_orig_line = original.lines().find(|l| !l.trim().is_empty()).unwrap_or("");
        let first_patch_line = patch.lines().find(|l| !l.trim().is_empty()).unwrap_or("");

        // If function name was altered, reject
        if let Some(fn_name) = extract_fn_name(first_orig_line) {
            if !first_patch_line.contains(&fn_name) {
                return false;
            }
        }
    }

    // Patch line count should stay proportional to original (not 5x blowup or wipeout)
    let orig_lines = original.lines().count();
    let patch_lines = patch.lines().count();
    if patch_lines < 2 || (orig_lines > 3 && patch_lines > orig_lines * 4) {
        return false;
    }

    true
}

fn extract_fn_name(line: &str) -> Option<String> {
    let re = Regex::new(r#"(?:def|function|func)\s+([a-zA-Z0-9_$]+)"#).ok()?;
    re.captures(line).and_then(|c| c.get(1)).map(|m| m.as_str().to_string())
}

fn check_import_statement(import_stmt: &str, context: &PreciseContext) -> bool {
    let trimmed = import_stmt.trim();
    if trimmed.is_empty() {
        return false;
    }

    let is_python = context.language.eq_ignore_ascii_case("python") || context.language.eq_ignore_ascii_case("py");
    if is_python {
        trimmed.starts_with("from ") || trimmed.starts_with("import ")
    } else {
        trimmed.starts_with("import ") || trimmed.starts_with("const ")
    }
}

fn check_schema_naming(schema: &str, import_stmt: &str) -> bool {
    let raw = format!("{} {}", schema, import_stmt);
    if raw.contains("http://") || raw.contains("https://") {
        return false;
    }

    // Check that schema name ends in Schema or Model
    let re = Regex::new(r#"(?:export const|class|type)\s+([a-zA-Z0-9_]+)"#).unwrap();
    if let Some(cap) = re.captures(schema) {
        if let Some(name) = cap.get(1) {
            let n = name.as_str();
            return n.ends_with("Schema") || n.ends_with("Model");
        }
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::engines::context_extractor::extract_precise_context;
    use serde_json::json;

    #[test]
    fn test_ast_verify_valid_zod_patch() {
        let code = "export async function getPayment(id: string) {\n  const res = await fetch(`https://api.stripe.com/${id}`);\n  const data = await res.json();\n  return data;\n}";
        let ctx = extract_precise_context(code, "test.ts", 2, "https://api.stripe.com", &[], "typescript");

        let patch = "export async function getPayment(id: string) {\n  const res = await fetch(`https://api.stripe.com/${id}`);\n  const data = PaymentSchema.parse(await res.json());\n  return data;\n}";
        let schema = "import { z } from 'zod';\nexport const PaymentSchema = z.object({ id: z.string() });";
        let import_stmt = "import { PaymentSchema } from './schemas/payment';";

        let result = ast_verify(code, patch, schema, import_stmt, &ctx);
        assert!(result.is_valid(), "Errors: {:?}", result.error_messages);
        assert!(result.syntactically_valid);
        assert!(result.schema_wired);
        assert!(result.no_silent_catch);
        assert!(result.blast_radius_clean);
        assert!(result.imports_correct);
        assert!(result.naming_valid);
    }

    #[test]
    fn test_ast_verify_rejects_silent_catch() {
        let code = "export async function getPayment() {\n  const res = await fetch('https://api.stripe.com');\n  return await res.json();\n}";
        let ctx = extract_precise_context(code, "test.ts", 2, "https://api.stripe.com", &[], "typescript");

        let bad_patch = "export async function getPayment() {\n  try {\n    const res = await fetch('https://api.stripe.com');\n    return PaymentSchema.parse(await res.json());\n  } catch (err) {\n    return null;\n  }\n}";
        let schema = "export const PaymentSchema = z.object({});";
        let import_stmt = "import { PaymentSchema } from './schemas/payment';";

        let result = ast_verify(code, bad_patch, schema, import_stmt, &ctx);
        assert!(!result.is_valid());
        assert!(!result.no_silent_catch);
        assert!(result.error_messages.iter().any(|m| m.contains("No-Swallow")));
    }
}
