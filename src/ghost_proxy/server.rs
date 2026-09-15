// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

use super::exchange::HttpExchange;
use axum::{
    body::Body,
    extract::{Request, State},
    http::{header, HeaderMap, HeaderName, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
    routing::any,
    Json, Router,
};
use serde_json::json;
use std::sync::Arc;
use tokio::sync::{oneshot, Mutex};

#[derive(Clone)]
pub struct GhostProxyState {
    pub exchanges: Vec<HttpExchange>,
    pub request_log: Arc<Mutex<Vec<String>>>,
}

pub struct GhostProxyHandle {
    pub port: u16,
    pub proxy_url: String,
    shutdown_tx: Option<oneshot::Sender<()>>,
}

impl GhostProxyHandle {
    pub fn stop(mut self) {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
    }
}

impl Drop for GhostProxyHandle {
    fn drop(&mut self) {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
    }
}

pub async fn start_ghost_proxy(
    port: u16,
    exchanges: Vec<HttpExchange>,
) -> Result<GhostProxyHandle, Box<dyn std::error::Error + Send + Sync>> {
    let state = GhostProxyState {
        exchanges,
        request_log: Arc::new(Mutex::new(Vec::new())),
    };

    let app = Router::new()
        .fallback(any(handle_proxy_request))
        .with_state(state);

    let addr = format!("127.0.0.1:{}", port);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    let actual_port = listener.local_addr()?.port();
    let proxy_url = format!("http://127.0.0.1:{}", actual_port);

    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();

    tokio::spawn(async move {
        let server = axum::serve(listener, app);
        let _ = server
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
            })
            .await;
    });

    Ok(GhostProxyHandle {
        port: actual_port,
        proxy_url,
        shutdown_tx: Some(shutdown_tx),
    })
}

async fn handle_proxy_request(
    State(state): State<GhostProxyState>,
    req: Request,
) -> Response {
    let method = req.method().to_string();
    let uri = req.uri();
    
    // Check if client forwarded the original target via custom header
    let original_url_header = req
        .headers()
        .get("x-boundary-original-url")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string());

    let target_path = original_url_header.unwrap_or_else(|| {
        let path = uri.path();
        if let Some(query) = uri.query() {
            format!("{}?{}", path, query)
        } else {
            path.to_string()
        }
    });

    {
        let mut log = state.request_log.lock().await;
        log.push(format!("{} {}", method, target_path));
    }

    for exchange in &state.exchanges {
        if exchange.matches(&method, &target_path) {
            let status = StatusCode::from_u16(exchange.response_status)
                .unwrap_or(StatusCode::OK);

            let mut header_map = HeaderMap::new();
            header_map.insert(
                header::CONTENT_TYPE,
                HeaderValue::from_static("application/json"),
            );
            header_map.insert(
                HeaderName::from_static("x-boundary-mock-hit"),
                HeaderValue::from_static("true"),
            );

            for (k, v) in &exchange.response_headers {
                if let (Ok(name), Ok(val)) = (
                    HeaderName::from_bytes(k.as_bytes()),
                    HeaderValue::from_str(v),
                ) {
                    header_map.insert(name, val);
                }
            }

            let body_bytes = serde_json::to_vec(&exchange.response_body)
                .unwrap_or_else(|_| b"{}".to_vec());

            return (status, header_map, Body::from(body_bytes)).into_response();
        }
    }

    let err_payload = json!({
        "error": "Boundary Ghost Proxy: unmocked network boundary",
        "method": method,
        "path": target_path,
        "message": "No recorded HttpExchange matched this request. Outbound network access is strictly blocked inside the sandbox."
    });

    let mut header_map = HeaderMap::new();
    header_map.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    header_map.insert(
        HeaderName::from_static("x-boundary-mock-hit"),
        HeaderValue::from_static("false"),
    );

    (StatusCode::NOT_FOUND, header_map, Json(err_payload)).into_response()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_ghost_proxy_serves_canned_response() {
        let exchange = HttpExchange::new(
            "POST",
            "/v1/payment_intents",
            200,
            json!({ "id": "pi_mocked_123", "status": "requires_payment_method" }),
        );

        let proxy = start_ghost_proxy(0, vec![exchange]).await.unwrap();
        assert!(proxy.port > 0);

        let app = Router::new()
            .fallback(any(handle_proxy_request))
            .with_state(GhostProxyState {
                exchanges: vec![HttpExchange::new(
                    "POST",
                    "/v1/payment_intents",
                    200,
                    json!({ "id": "pi_mocked_123" }),
                )],
                request_log: Arc::new(Mutex::new(Vec::new())),
            });

        let req = axum::http::Request::builder()
            .method("POST")
            .uri("/v1/payment_intents")
            .body(Body::empty())
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(
            resp.headers().get("x-boundary-mock-hit").unwrap(),
            "true"
        );

        proxy.stop();
    }

    #[tokio::test]
    async fn test_ghost_proxy_unmatched_returns_404() {
        let app = Router::new()
            .fallback(any(handle_proxy_request))
            .with_state(GhostProxyState {
                exchanges: vec![],
                request_log: Arc::new(Mutex::new(Vec::new())),
            });

        let req = axum::http::Request::builder()
            .method("GET")
            .uri("/v1/unmocked_endpoint")
            .body(Body::empty())
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
        assert_eq!(
            resp.headers().get("x-boundary-mock-hit").unwrap(),
            "false"
        );
    }
}
