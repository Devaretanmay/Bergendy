use axum::{
    routing::post,
    Router,
    Json,
    extract::State,
};
use serde_json::Value;
use std::sync::Arc;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;

pub struct AppState {
    knowledge_dir: PathBuf,
}

pub async fn start_collector(port: u16) {
    let mut knowledge_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    knowledge_dir.push(".boundary");
    knowledge_dir.push("knowledge");
    
    std::fs::create_dir_all(&knowledge_dir).unwrap_or_default();
    
    let state = Arc::new(AppState {
        knowledge_dir,
    });

    let app = Router::new()
        .route("/v1/traces", post(handle_traces))
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    println!("OTEL Collector listening on {}", addr);
    
    axum::serve(listener, app).await.unwrap();
}

async fn handle_traces(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<Value>,
) {
    // Parse OTLP JSON payload and extract response bodies
    if let Some(resource_spans) = payload.get("resourceSpans").and_then(|v| v.as_array()) {
        for rs in resource_spans {
            if let Some(scope_spans) = rs.get("scopeSpans").and_then(|v| v.as_array()) {
                for ss in scope_spans {
                    if let Some(spans) = ss.get("spans").and_then(|v| v.as_array()) {
                        for span in spans {
                            extract_and_save_response(&state, span);
                        }
                    }
                }
            }
        }
    }
}

fn extract_and_save_response(state: &AppState, span: &Value) {
    if let Some(attributes) = span.get("attributes").and_then(|v| v.as_array()) {
        let mut response_body = None;
        let mut request_body = None;
        let mut url = None;
        let mut method = "GET".to_string();
        let mut status_code: u16 = 200;

        for attr in attributes {
            let key = attr.get("key").and_then(|v| v.as_str()).unwrap_or("");
            if key == "http.response.body" {
                response_body = attr.get("value").and_then(|v| v.get("stringValue")).and_then(|v| v.as_str());
            } else if key == "http.request.body" {
                request_body = attr.get("value").and_then(|v| v.get("stringValue")).and_then(|v| v.as_str());
            } else if key == "http.url" || key == "http.target" {
                url = attr.get("value").and_then(|v| v.get("stringValue")).and_then(|v| v.as_str());
            } else if key == "http.method" {
                if let Some(m) = attr.get("value").and_then(|v| v.get("stringValue")).and_then(|v| v.as_str()) {
                    method = m.to_uppercase();
                }
            } else if key == "http.status_code" {
                if let Some(sc) = attr.get("value").and_then(|v| v.get("intValue")).and_then(|v| v.as_i64()) {
                    status_code = sc as u16;
                }
            }
        }

        if let (Some(body_str), Some(u)) = (response_body, url) {
            let safe_name = u.replace("://", "_").replace('/', "_").replace('?', "_");
            let mut file_path = state.knowledge_dir.clone();
            file_path.push(format!("{}.json", safe_name));

            if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&file_path) {
                let _ = writeln!(file, "{}", body_str);
            }

            // Construct full HttpExchange for Ghost Proxy
            let resp_json: Value = serde_json::from_str(body_str)
                .unwrap_or_else(|_| serde_json::json!({ "raw": body_str }));

            let mut exchange = crate::ghost_proxy::HttpExchange::new(
                method,
                u,
                status_code,
                resp_json,
            );

            if let Some(rb_str) = request_body {
                exchange.request_body = serde_json::from_str(rb_str).ok();
            }

            let mut jsonl_path = state.knowledge_dir.clone();
            jsonl_path.push("exchanges.jsonl");
            let _ = exchange.append_to_jsonl(&jsonl_path);

            let mut ex_dir = state.knowledge_dir.clone();
            ex_dir.push("exchanges");
            let mut ex_file = ex_dir.clone();
            ex_file.push(format!("{}.json", safe_name));
            let _ = exchange.save_to_file(&ex_file);
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_otel_collector_compiles() {
        assert!(true);
    }
}
