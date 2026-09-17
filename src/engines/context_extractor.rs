// Copyright 2026 Bergendy Authors
// SPDX-License-Identifier: Apache-2.0

use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataFlowNode {
    pub code: String,
    pub line: usize,
    pub variable_name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ErrorHandlingPattern {
    TryCatch { catch_block: String },
    PromiseCatch { handler: String },
    CustomHandler { function_name: String },
    #[serde(other)]
    None,
}

impl Default for ErrorHandlingPattern {
    fn default() -> Self {
        ErrorHandlingPattern::None
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PreciseContext {
    #[serde(default)]
    pub file: String,
    #[serde(default)]
    pub line: usize,
    #[serde(default)]
    pub column: usize,
    #[serde(default)]
    pub callsite_code: String,

    #[serde(default)]
    pub enclosing_function_code: String,
    #[serde(default)]
    pub function_signature: String,
    #[serde(default)]
    pub function_start_line: usize,
    #[serde(default)]
    pub function_end_line: usize,

    #[serde(default)]
    pub data_flow: Vec<DataFlowNode>,
    #[serde(default)]
    pub error_handling: ErrorHandlingPattern,
    #[serde(default)]
    pub existing_imports: Vec<String>,

    #[serde(default)]
    pub traffic_samples: Vec<serde_json::Value>,
    #[serde(default)]
    pub traffic_sample_count: usize,

    #[serde(default)]
    pub language: String,
    #[serde(default)]
    pub validation_library: String,
}

impl PreciseContext {
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

/// Extracts precise context around a callsite in a source file.
pub fn extract_precise_context(
    source_code: &str,
    file_path: &str,
    target_line: usize,
    endpoint: &str,
    traffic_samples: &[serde_json::Value],
    lang: &str,
) -> PreciseContext {
    let lines: Vec<&str> = source_code.lines().collect();
    let total_lines = lines.len();

    let target_idx = if target_line > 0 && target_line <= total_lines {
        target_line - 1
    } else {
        lines
            .iter()
            .position(|l| l.contains(endpoint))
            .unwrap_or(0)
    };

    let callsite_code = lines.get(target_idx).unwrap_or(&"").trim().to_string();
    let col = lines
        .get(target_idx)
        .and_then(|l| l.find(endpoint))
        .unwrap_or(0)
        + 1;

    let (start_line, end_line, sig, func_code) =
        find_enclosing_function(&lines, target_idx, lang);

    let data_flow = extract_data_flow(&lines, target_idx, end_line);
    let error_handling = detect_error_handling(&lines, start_line, end_line, target_idx);
    let existing_imports = extract_existing_imports(&lines, lang);

    let validation_library = match lang.to_lowercase().as_str() {
        "python" | "py" => "pydantic".to_string(),
        "go" => "struct".to_string(),
        _ => "zod".to_string(),
    };

    let sample_slice = if traffic_samples.len() > 5 {
        traffic_samples[..5].to_vec()
    } else {
        traffic_samples.to_vec()
    };

    PreciseContext {
        file: file_path.to_string(),
        line: target_idx + 1,
        column: col,
        callsite_code,
        enclosing_function_code: func_code,
        function_signature: sig,
        function_start_line: start_line + 1,
        function_end_line: end_line + 1,
        data_flow,
        error_handling,
        existing_imports,
        traffic_samples: sample_slice,
        traffic_sample_count: traffic_samples.len(),
        language: lang.to_string(),
        validation_library,
    }
}

fn find_enclosing_function(
    lines: &[&str],
    target_idx: usize,
    lang: &str,
) -> (usize, usize, String, String) {
    if lines.is_empty() {
        return (0, 0, String::new(), String::new());
    }

    let is_python = lang.eq_ignore_ascii_case("python") || lang.eq_ignore_ascii_case("py");
    let is_go = lang.eq_ignore_ascii_case("go");

    let mut start_idx = target_idx;
    let mut signature = String::new();
    let mut found_start = false;

    // Scan upward from callsite to find function definition
    for i in (0..=target_idx).rev() {
        let line = lines[i].trim();
        if is_python {
            if line.starts_with("def ") || line.starts_with("async def ") {
                start_idx = i;
                signature = line.to_string();
                found_start = true;
                break;
            }
        } else if is_go {
            if line.starts_with("func ") {
                start_idx = i;
                signature = line.to_string();
                found_start = true;
                break;
            }
        } else {
            // TypeScript / JavaScript
            if line.starts_with("function ")
                || line.starts_with("async function ")
                || line.starts_with("export function ")
                || line.starts_with("export async function ")
                || line.contains("=>")
                || line.contains("function(")
            {
                start_idx = i;
                signature = line.to_string();
                found_start = true;
                break;
            }
        }
    }

    if !found_start {
        // Fallback: window of 10 lines around target
        start_idx = target_idx.saturating_sub(5);
        let end_idx = (target_idx + 10).min(lines.len().saturating_sub(1));
        let code = lines[start_idx..=end_idx].join("\n");
        return (start_idx, end_idx, "anonymous_scope".to_string(), code);
    }

    // Determine end of function
    let mut end_idx = target_idx;
    if is_python {
        // Indentation-based scope
        let base_indent = lines[start_idx]
            .chars()
            .take_while(|c| c.is_whitespace())
            .count();
        end_idx = lines.len().saturating_sub(1);
        for (i, line) in lines.iter().enumerate().skip(start_idx + 1) {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            let cur_indent = line.chars().take_while(|c| c.is_whitespace()).count();
            if cur_indent <= base_indent {
                end_idx = i.saturating_sub(1);
                break;
            }
        }
    } else {
        // Brace-counting scope
        let mut depth: i32 = 0;
        let mut seen_open = false;
        for (i, line) in lines.iter().enumerate().skip(start_idx) {
            for ch in line.chars() {
                if ch == '{' {
                    depth += 1;
                    seen_open = true;
                } else if ch == '}' {
                    depth -= 1;
                }
            }
            if seen_open && depth <= 0 {
                end_idx = i;
                break;
            }
        }
        if !seen_open || depth > 0 {
            end_idx = (target_idx + 15).min(lines.len().saturating_sub(1));
        }
    }

    let code = lines[start_idx..=end_idx].join("\n");
    (start_idx, end_idx, signature, code)
}

fn extract_data_flow(lines: &[&str], target_idx: usize, end_idx: usize) -> Vec<DataFlowNode> {
    let mut nodes = Vec::new();
    let assignment_re = Regex::new(r#"(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*="#).unwrap();

    for i in target_idx..=end_idx {
        if i >= lines.len() {
            break;
        }
        let line = lines[i].trim();
        if line.contains(".json()")
            || line.contains(".text()")
            || line.contains(".data")
            || line.contains("response.json()")
            || line.contains("res.json()")
            || line.contains(".then(")
        {
            let var_name = assignment_re
                .captures(line)
                .and_then(|c| c.get(1))
                .map(|m| m.as_str().to_string());

            nodes.push(DataFlowNode {
                code: line.to_string(),
                line: i + 1,
                variable_name: var_name,
            });
        }
    }
    nodes
}

fn detect_error_handling(
    lines: &[&str],
    start_idx: usize,
    end_idx: usize,
    target_idx: usize,
) -> ErrorHandlingPattern {
    let mut in_try = false;
    for i in start_idx..=target_idx {
        if i >= lines.len() {
            break;
        }
        let line = lines[i].trim();
        if line.starts_with("try") || line.contains("try {") || line.starts_with("try:") {
            in_try = true;
            break;
        }
    }
    if in_try {
        for i in target_idx..=end_idx {
            if i >= lines.len() {
                break;
            }
            let line = lines[i].trim();
            if line.contains("catch") || line.starts_with("except") {
                return ErrorHandlingPattern::TryCatch { catch_block: line.to_string() };
            }
        }
    }

    for i in target_idx..=end_idx {
        if i >= lines.len() {
            break;
        }
        let line = lines[i].trim();
        if line.contains(".catch(") {
            return ErrorHandlingPattern::PromiseCatch {
                handler: line.to_string(),
            };
        }
    }

    ErrorHandlingPattern::None
}

fn extract_existing_imports(lines: &[&str], lang: &str) -> Vec<String> {
    let mut imports = Vec::new();
    let is_python = lang.eq_ignore_ascii_case("python") || lang.eq_ignore_ascii_case("py");

    for line in lines.iter().take(50) {
        let trimmed = line.trim();
        if is_python {
            if trimmed.starts_with("import ") || trimmed.starts_with("from ") {
                imports.push(trimmed.to_string());
            }
        } else if trimmed.starts_with("import ") || (trimmed.starts_with("const ") && trimmed.contains("require(")) {
            imports.push(trimmed.to_string());
        }
    }
    imports
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_extract_precise_context_typescript() {
        let code = r#"
import { fetch } from 'undici';

export async function getStripePayment(id: string) {
    const response = await fetch(`https://api.stripe.com/v1/payment_intents/${id}`);
    const data = await response.json();
    return data;
}
"#;
        let samples = vec![json!({"id": "pi_123", "amount": 2000})];
        let ctx = extract_precise_context(
            code,
            "src/api.ts",
            5,
            "https://api.stripe.com/v1/payment_intents",
            &samples,
            "typescript",
        );

        assert_eq!(ctx.file, "src/api.ts");
        assert_eq!(ctx.validation_library, "zod");
        assert!(ctx.enclosing_function_code.contains("export async function getStripePayment"));
        assert!(ctx.enclosing_function_code.contains("const data = await response.json()"));
        assert_eq!(ctx.data_flow.len(), 1);
        assert_eq!(ctx.existing_imports.len(), 1);
        assert_eq!(ctx.traffic_sample_count, 1);
    }

    #[test]
    fn test_extract_precise_context_python() {
        let code = r#"
import requests

def fetch_weather(city: str):
    res = requests.get(f"https://api.weather.com/v1/{city}")
    data = res.json()
    return data
"#;
        let samples = vec![json!({"temp": 72})];
        let ctx = extract_precise_context(
            code,
            "weather.py",
            5,
            "https://api.weather.com/v1",
            &samples,
            "python",
        );

        assert_eq!(ctx.validation_library, "pydantic");
        assert!(ctx.enclosing_function_code.contains("def fetch_weather"));
        assert_eq!(ctx.data_flow.len(), 1);
    }
}
