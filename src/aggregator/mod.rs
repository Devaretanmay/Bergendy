// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

use crate::ghost_proxy::HttpExchange;
use blake3::Hasher;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

/// Extracts structural representation of a JSON value, replacing actual data
/// with type tags ("string", "number", "boolean", "null") and sorting object keys.
pub fn extract_json_structure(val: &Value) -> Value {
    match val {
        Value::Null => json!("null"),
        Value::Bool(_) => json!("boolean"),
        Value::Number(_) => json!("number"),
        Value::String(_) => json!("string"),
        Value::Array(arr) => {
            if arr.is_empty() {
                json!(["empty"])
            } else {
                // Collect unique element structures in the array
                let mut unique_elem_structures = Vec::new();
                let mut seen_hashes = HashSet::new();
                for elem in arr {
                    let elem_struct = extract_json_structure(elem);
                    let h = hash_json_structure(&elem_struct);
                    if seen_hashes.insert(h) {
                        unique_elem_structures.push(elem_struct);
                    }
                }
                Value::Array(unique_elem_structures)
            }
        }
        Value::Object(obj) => {
            let mut sorted_map = BTreeMap::new();
            for (k, v) in obj {
                sorted_map.insert(k.clone(), extract_json_structure(v));
            }
            let mut map = Map::new();
            for (k, v) in sorted_map {
                map.insert(k, v);
            }
            Value::Object(map)
        }
    }
}

pub fn hash_json_structure(structure: &Value) -> String {
    let canonical_str = serde_json::to_string(structure).unwrap_or_default();
    let mut hasher = Hasher::new();
    hasher.update(canonical_str.as_bytes());
    hasher.finalize().to_hex().to_string()
}

pub fn cluster_exchanges(exchanges: &[HttpExchange]) -> HashMap<String, Vec<Value>> {
    let mut clusters: HashMap<String, Vec<Value>> = HashMap::new();
    let mut seen_hashes_by_endpoint: HashMap<String, HashSet<String>> = HashMap::new();

    for exchange in exchanges {
        let key = format!("{} {}", exchange.request_method.to_uppercase(), exchange.request_path);
        let structure = extract_json_structure(&exchange.response_body);
        let struct_hash = hash_json_structure(&structure);

        let seen = seen_hashes_by_endpoint.entry(key.clone()).or_default();
        if seen.insert(struct_hash) {
            clusters.entry(key).or_default().push(exchange.response_body.clone());
        }
    }

    clusters
}

pub fn load_and_cluster(
    jsonl_path: &Path,
    endpoint_filter: Option<&str>,
) -> std::io::Result<HashMap<String, Vec<Value>>> {
    if !jsonl_path.exists() {
        return Ok(HashMap::new());
    }

    let file = File::open(jsonl_path)?;
    let reader = BufReader::new(file);
    let mut exchanges = Vec::new();

    for line in reader.lines() {
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        if let Ok(ex) = serde_json::from_str::<HttpExchange>(trimmed) {
            if let Some(filter) = endpoint_filter {
                if !ex.matches(&ex.request_method, filter) && !ex.request_path.contains(filter) {
                    continue;
                }
            }
            exchanges.push(ex);
        }
    }

    Ok(cluster_exchanges(&exchanges))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_extract_json_structure() {
        let val1 = json!({
            "id": "cus_123",
            "balance": 1500,
            "livemode": false,
            "metadata": null
        });

        let struct1 = extract_json_structure(&val1);
        assert_eq!(
            struct1,
            json!({
                "balance": "number",
                "id": "string",
                "livemode": "boolean",
                "metadata": "null"
            })
        );

        let val2 = json!({
            "livemode": true,
            "id": "cus_456",
            "metadata": null,
            "balance": 0
        });

        let struct2 = extract_json_structure(&val2);
        assert_eq!(struct1, struct2);
        assert_eq!(hash_json_structure(&struct1), hash_json_structure(&struct2));
    }

    #[test]
    fn test_cluster_exchanges_deduplication() {
        let ex1 = HttpExchange::new(
            "POST",
            "/v1/customers",
            200,
            json!({ "id": "cus_1", "email": "a@example.com" }),
        );
        let ex2 = HttpExchange::new(
            "POST",
            "/v1/customers",
            200,
            json!({ "id": "cus_2", "email": "b@example.com" }),
        );
        let ex3 = HttpExchange::new(
            "POST",
            "/v1/customers",
            200,
            json!({ "id": "cus_3", "email": "c@example.com", "discount": { "coupon": "SUMMER" } }),
        );

        let clustered = cluster_exchanges(&[ex1, ex2, ex3]);
        let samples = clustered.get("POST /v1/customers").unwrap();

        assert_eq!(samples.len(), 2);
        assert_eq!(samples[0]["id"], "cus_1");
        assert_eq!(samples[1]["id"], "cus_3");
    }
}
