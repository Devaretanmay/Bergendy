// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

use regex::Regex;

/// Injects Zod schema validation into TypeScript/JavaScript source code for a given endpoint.
/// Replaces unvalidated `fetch().then(r => r.json())` or `await res.json()` with `Schema.parse(...)`.
pub fn inject_schema_validation(
    source_code: &str,
    endpoint: &str,
    schema_name: &str,
    schema_import_path: &str,
) -> Result<String, String> {
    let mut modified = source_code.to_string();
    let clean_endpoint = endpoint.trim_matches('"').trim_matches('\'');

    let mut transformed = false;

    let promise_regex = Regex::new(
        r#"\.then\s*\(\s*(?:\(?\s*([a-zA-Z0-9_$]+)\s*\)?)\s*=>\s*([a-zA-Z0-9_$]+)\.json\s*\(\s*\)\s*\)"#,
    ).map_err(|e| e.to_string())?;

    if promise_regex.is_match(&modified) && modified.contains(clean_endpoint) {
        let replacement = format!(
            ".then($1 => $2.json()).then(data => {}.parse(data))",
            schema_name
        );
        modified = promise_regex.replace(&modified, replacement.as_str()).to_string();
        transformed = true;
    }

    let await_regex = Regex::new(
        r#"(const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*await\s+([a-zA-Z0-9_$]+)\.json\s*\(\s*\)"#,
    ).map_err(|e| e.to_string())?;

    if !transformed && await_regex.is_match(&modified) {
        let replacement = format!(
            "$1 $2 = {}.parse(await $3.json())",
            schema_name
        );
        modified = await_regex.replace(&modified, replacement.as_str()).to_string();
        transformed = true;
    }

    let return_await_regex = Regex::new(
        r#"return\s+await\s+([a-zA-Z0-9_$]+)\.json\s*\(\s*\)"#,
    ).map_err(|e| e.to_string())?;

    if !transformed && return_await_regex.is_match(&modified) {
        let replacement = format!(
            "return {}.parse(await $1.json())",
            schema_name
        );
        modified = return_await_regex.replace(&modified, replacement.as_str()).to_string();
        transformed = true;
    }

    if transformed || modified.contains(schema_name) {
        let import_statement = format!(
            "import {{ {} }} from '{}';\n",
            schema_name, schema_import_path
        );

        if !modified.contains(&format!("import {{ {} }}", schema_name))
            && !modified.contains(&format!("import {{{}}}", schema_name))
        {
            let mut last_import_end = 0;
            for line_match in Regex::new(r#"(?m)^import\s+.*?;?\s*$"#).unwrap().find_iter(&modified) {
                last_import_end = line_match.end();
            }

            if last_import_end > 0 {
                let mut with_import = String::new();
                with_import.push_str(&modified[..last_import_end]);
                with_import.push('\n');
                with_import.push_str(&import_statement);
                with_import.push_str(&modified[last_import_end..]);
                modified = with_import;
            } else {
                modified = format!("{}{}", import_statement, modified);
            }
        }
    }

    Ok(modified)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inject_promise_chain() {
        let original = r#"
import { useEffect } from 'react';

export function loadCustomers() {
  return fetch('/v1/customers')
    .then(res => res.json());
}
"#;

        let rewritten = inject_schema_validation(
            original,
            "/v1/customers",
            "StripeCustomerSchema",
            "@/schemas/stripe_customers",
        )
        .unwrap();

        assert!(rewritten.contains("import { StripeCustomerSchema } from '@/schemas/stripe_customers';"));
        assert!(rewritten.contains(".then(res => res.json()).then(data => StripeCustomerSchema.parse(data))"));
    }

    #[test]
    fn test_inject_await_assignment() {
        let original = r#"
export async function getCustomer(id: string) {
  const res = await fetch(`/v1/customers/${id}`);
  const data = await res.json();
  return data;
}
"#;

        let rewritten = inject_schema_validation(
            original,
            "/v1/customers",
            "StripeCustomerSchema",
            "@/schemas/stripe_customers",
        )
        .unwrap();

        assert!(rewritten.contains("import { StripeCustomerSchema } from '@/schemas/stripe_customers';"));
        assert!(rewritten.contains("const data = StripeCustomerSchema.parse(await res.json());"));
    }
}
