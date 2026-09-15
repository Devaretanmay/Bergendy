// Copyright 2026 Boundary Authors
// SPDX-License-Identifier: Apache-2.0

pub mod exchange;
pub mod server;

pub use exchange::HttpExchange;
pub use server::{start_ghost_proxy, GhostProxyHandle, GhostProxyState};

use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

static PROXY_REGISTRY: OnceLock<Arc<Mutex<HashMap<u16, GhostProxyHandle>>>> = OnceLock::new();

fn get_registry() -> &'static Arc<Mutex<HashMap<u16, GhostProxyHandle>>> {
    PROXY_REGISTRY.get_or_init(|| Arc::new(Mutex::new(HashMap::new())))
}

/// Spawns a ghost proxy on the tokio runtime and registers it.
pub fn spawn_and_register_ghost_proxy(
    port: u16,
    exchanges: Vec<HttpExchange>,
) -> Result<(u16, String), String> {
    let rt = tokio::runtime::Handle::try_current();
    match rt {
        Ok(handle) => {
            let res = tokio::task::block_in_place(|| {
                handle.block_on(async {
                    start_ghost_proxy(port, exchanges)
                        .await
                        .map_err(|e| e.to_string())
                })
            })?;
            let p = res.port;
            let url = res.proxy_url.clone();
            get_registry().lock().unwrap().insert(p, res);
            Ok((p, url))
        }
        Err(_) => {
            let (tx, rx) = std::sync::mpsc::channel();
            std::thread::spawn(move || {
                let rt = match tokio::runtime::Builder::new_current_thread()
                    .enable_all()
                    .build()
                {
                    Ok(r) => r,
                    Err(e) => {
                        let _ = tx.send(Err(e.to_string()));
                        return;
                    }
                };
                rt.block_on(async {
                    match start_ghost_proxy(port, exchanges).await {
                        Ok(handle) => {
                            let p = handle.port;
                            let url = handle.proxy_url.clone();
                            get_registry().lock().unwrap().insert(p, handle);
                            let _ = tx.send(Ok((p, url)));
                            std::future::pending::<()>().await;
                        }
                        Err(e) => {
                            let _ = tx.send(Err(e.to_string()));
                        }
                    }
                });
            });
            rx.recv().map_err(|e| e.to_string())?
        }
    }
}

pub fn stop_ghost_proxy(port: u16) -> bool {
    let mut reg = get_registry().lock().unwrap();
    if let Some(handle) = reg.remove(&port) {
        handle.stop();
        true
    } else {
        false
    }
}

pub fn stop_all_ghost_proxies() {
    let mut reg = get_registry().lock().unwrap();
    for (_, handle) in reg.drain() {
        handle.stop();
    }
}
