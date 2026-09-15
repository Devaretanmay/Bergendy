// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

/// Represents a full HTTP request/response exchange captured from live traffic or OpenTelemetry spans.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct HttpExchange {
    pub request_method: String,
    pub request_path: String,
    #[serde(default)]
    pub request_headers: HashMap<String, String>,
    #[serde(default)]
    pub request_body: Option<Value>,

    pub response_status: u16,
    #[serde(default)]
    pub response_headers: HashMap<String, String>,
    pub response_body: Value,
}

impl HttpExchange {
    pub fn new(
        method: impl Into<String>,
        path: impl Into<String>,
        status: u16,
        response_body: Value,
    ) -> Self {
        let mut response_headers = HashMap::new();
        response_headers.insert("content-type".to_string(), "application/json".to_string());

        Self {
            request_method: method.into().to_uppercase(),
            request_path: path.into(),
            request_headers: HashMap::new(),
            request_body: None,
            response_status: status,
            response_headers,
            response_body,
        }
    }

    /// Check if an incoming HTTP request matches this captured exchange.
    /// Supports both relative paths (`/v1/charges`) and absolute proxy targets (`https://api.stripe.com/v1/charges`).
    pub fn matches(&self, method: &str, target_url_or_path: &str) -> bool {
        if !self.request_method.eq_ignore_ascii_case(method) {
            return false;
        }

        let incoming_clean = Self::extract_path_and_query(target_url_or_path);
        let captured_clean = Self::extract_path_and_query(&self.request_path);

        if incoming_clean == captured_clean {
            return true;
        }

        let incoming_path = incoming_clean.split('?').next().unwrap_or("");
        let captured_path = captured_clean.split('?').next().unwrap_or("");

        incoming_path.trim_end_matches('/') == captured_path.trim_end_matches('/')
    }

    fn extract_path_and_query(input: &str) -> String {
        if let Some(idx) = input.find("://") {
            let after_scheme = &input[idx + 3..];
            if let Some(slash_idx) = after_scheme.find('/') {
                return after_scheme[slash_idx..].to_string();
            }
            return "/".to_string();
        }
        if !input.starts_with('/') {
            format!("/{}", input)
        } else {
            input.to_string()
        }
    }

    pub fn save_to_file(&self, path: &Path) -> std::io::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let data = serde_json::to_string_pretty(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        fs::write(path, data)
    }

    pub fn append_to_jsonl(&self, path: &Path) -> std::io::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let line = serde_json::to_string(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut file = OpenOptions::new().create(true).append(true).open(path)?;
        writeln!(file, "{}", line)
    }

    pub fn load_from_file(path: &Path) -> std::io::Result<Self> {
        let content = fs::read_to_string(path)?;
        serde_json::from_str(&content)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    pub fn load_from_jsonl(path: &Path) -> std::io::Result<Vec<Self>> {
        if !path.exists() {
            return Ok(Vec::new());
        }
        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let mut exchanges = Vec::new();
        for line in reader.lines() {
            let line = line?;
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if let Ok(ex) = serde_json::from_str::<Self>(trimmed) {
                exchanges.push(ex);
            }
        }
        Ok(exchanges)
    }

    pub fn load_from_dir(dir: &Path) -> std::io::Result<Vec<Self>> {
        if !dir.exists() {
            return Ok(Vec::new());
        }
        let mut exchanges = Vec::new();
        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) == Some("json") {
                if let Ok(ex) = Self::load_from_file(&path) {
                    exchanges.push(ex);
                }
            }
        }
        Ok(exchanges)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_exchange_creation_and_matching() {
        let exchange = HttpExchange::new(
            "POST",
            "/v1/payment_intents",
            200,
            json!({ "id": "pi_123", "amount": 2000, "status": "succeeded" }),
        );

        assert!(exchange.matches("POST", "/v1/payment_intents"));
        assert!(exchange.matches("post", "/v1/payment_intents/"));
        assert!(exchange.matches("POST", "https://api.stripe.com/v1/payment_intents"));
        assert!(exchange.matches("POST", "https://api.stripe.com/v1/payment_intents?client_secret=secret"));
        assert!(!exchange.matches("GET", "/v1/payment_intents"));
        assert!(!exchange.matches("POST", "/v1/customers"));
    }

    #[test]
    fn test_exchange_json_roundtrip() {
        let ex = HttpExchange::new("GET", "/v1/charges/ch_1", 200, json!({"id": "ch_1"}));
        let serialized = serde_json::to_string(&ex).unwrap();
        let deserialized: HttpExchange = serde_json::from_str(&serialized).unwrap();
        assert_eq!(ex, deserialized);
    }
}
