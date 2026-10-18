# sub-REALTIME-IOT-DESKTOP — WebSockets/SSE/WebRTC, IoT (MQTT), Electron/Tauri & Chrome Extensions

Use when building realtime communication layers (WebSockets, Server-Sent Events, WebRTC), IoT/edge telemetry pipelines
(MQTT), cross-platform desktop applications (Tauri, Electron), or browser extensions (Chrome Manifest V3).

## 1. Realtime: WebSockets, Server-Sent Events (SSE) & WebRTC rules

- **Pick the simplest protocol that fits**:
  - **SSE (`EventSource` / Fetch stream)**: server-to-client push (AI token streaming, live notifications, order status tickers,
    dashboards). Works over standard HTTP/2, automatic reconnection, simpler proxy config (`X-Accel-Buffering: no`).
  - **WebSockets (`ws` / Socket.IO)**: low-latency bidirectional messaging (chat, collaborative editing, multiplayer, trading).
  - **WebRTC**: peer-to-peer or SFU media streaming (audio/video calls, screen sharing) and unreliable/ordered UDP data channels.
- **WebSocket production rules**:
  - **Authentication**: authenticate during the handshake (short-lived ticket/token or HttpOnly cookie with strict `Origin` header validation — browsers do NOT enforce CORS on WebSocket handshakes, so always verify `Origin` against an allowlist to prevent Cross-Site WebSocket Hijacking).
  - **Heartbeat & dead-connection cleanup**: implement server ping/pong intervals (e.g., every 25–30s) and terminate zombie sockets that miss 2 pongs.
  - **Client reconnection**: exponential backoff with full jitter (`min(30s, base * 2^attempt + jitter)`) plus state catch-up (`last_event_id` cursor) on reconnect so no messages are lost during brief disconnects.
  - **Horizontal scaling**: stateless socket servers require a Pub/Sub backplane (Redis Pub/Sub / NATS / Kafka) so User A on Node 1 receives messages published on Node 2.
  - **Backpressure**: check `ws.bufferedAmount` before pushing high-frequency streams; drop or coalesce stale frames for slow clients rather than exhausting server RAM.

## 2. IoT & Edge Telemetry (MQTT, Modbus, Edge Gateways) rules

- **MQTT topic hierarchy**:
  - Structure topics cleanly: `v1/<tenant_id>/<site_id>/<device_type>/<device_id>/<telemetry|command|state|lwt>`.
  - Never use a leading slash (`/v1/...` creates an empty root topic level); never subscribe to `#` at root in high-throughput production consumers (use `$share/<group>/<topic>` shared subscriptions for load-balanced worker pools).
- **QoS & reliability**:
  - **QoS 0 (At most once)**: high-frequency non-critical sensor readings (e.g., temperature every second).
  - **QoS 1 (At least once)**: critical alarms, state changes, commands (consumers MUST be idempotent using `message_id` + `timestamp`).
  - **Last Will and Testament (LWT)** + Retained Status message on `.../state` (`{"online": false}`) to detect sudden device power/network loss.
- **Device security & offline buffering**:
  - Unique per-device identity (mTLS X.509 client certificates or unique per-device credentials — never one shared password across all devices).
  - Topic ACLs at the broker (EMQX / Mosquitto / AWS IoT): a device may only publish/subscribe to its own `<device_id>` subtree.
  - Buffer telemetry locally on the edge gateway (SQLite/ring buffer) during internet outages and flush in timestamped batches on reconnect.

## 3. Desktop Apps: Tauri & Electron security and architecture rules

- **Process isolation (non-negotiable)**:
  - **Electron**: `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`. Expose only a narrow, typed API
    surface via `contextBridge.exposeInMainWorld` in the `preload` script — never expose raw `ipcRenderer` or `fs`/`child_process` to the renderer UI.
  - **Tauri**: scope capabilities/permissions narrowly per window (`capabilities/*.json`); validate all `#[tauri::command]`
    arguments in Rust; never enable unrestricted shell or global filesystem access for untrusted web content.
- **Navigation & external links**: block in-app window navigation (`will-navigate` / `setWindowOpenHandler`) to external
  URLs; open external `https://` links in the OS default browser after protocol validation (block `file://`, `javascript:`, custom RCE schemes).
- **Auto-updates**: verify cryptographic signatures on all application update bundles before installation.

## 4. Chrome / Browser Extensions (Manifest V3) rules

- **Manifest V3 service worker lifecycle**: background service workers are **ephemeral** and terminate after ~30s of
  inactivity. Never store state in global JS variables; persist state in `chrome.storage.local` or `chrome.storage.session`,
  and use `chrome.alarms` instead of `setInterval`.
- **Least-privilege permissions**: request only the minimal `permissions` and `host_permissions` required (`activeTab` over
  `<all_urls>` whenever possible) to pass Chrome Web Store review quickly.
- **Content script isolation**: content scripts share the DOM (not JS globals) with untrusted web pages — validate every
  `window.postMessage` / `chrome.runtime.onMessage` sender (`sender.id`, `sender.url`) and never inject unsanitized data via `innerHTML`.
