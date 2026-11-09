# 02 — Nginx & Caddy Reverse Proxy, SSL & Edge Hardening

Pair with downloaded H5BP configs in [`vendor/H5BP_nginx_main.conf`](vendor/H5BP_nginx_main.conf), [`vendor/H5BP_nginx_ssl_engine.conf`](vendor/H5BP_nginx_ssl_engine.conf), and [`vendor/H5BP_nginx_compression.conf`](vendor/H5BP_nginx_compression.conf).

---

## 1. Production Nginx Reverse Proxy Template (`/etc/nginx/conf.d/app.conf`)

Includes:
- Version hiding (`server_tokens off;`)
- Rate-limiting zones (`limit_req_zone` for auth/login and general API)
- Upstream keepalive connection pooling
- TLS 1.2 / 1.3 modern cipher hardening & HSTS
- WebSocket & Server-Sent Events (SSE) support
- Anti-Slowloris timeout & buffer protections

```nginx
# Rate limit zones (10MB shared memory ~ 160,000 IPs)
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_conn_zone $binary_remote_addr zone=addr_conn:10m;

upstream app_backend {
    server 127.0.0.1:3000 max_fails=3 fail_timeout=15s;
    keepalive 64;
}

server {
    listen 80;
    listen [::]:80;
    server_name app.example.com;
    server_tokens off;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name app.example.com;
    server_tokens off;

    # TLS 1.2 & 1.3 Hardening
    ssl_certificate     /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Anti-Slowloris & Body Size Bounds
    client_max_body_size 20M;
    client_body_timeout 15s;
    client_header_timeout 15s;
    keepalive_timeout 30s;
    send_timeout 15s;

    # Auth Endpoint Rate Limit (Strict Brute-Force Protection)
    location ~ ^/api/v1/auth/(login|register|forgot-password) {
        limit_req zone=auth_limit burst=5 nodelay;
        limit_req_status 429;
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE / Streaming Endpoints (Disable Proxy Buffering)
    location /api/v1/stream {
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # General API & WebSocket Proxy
    location / {
        limit_req zone=api_limit burst=60 nodelay;
        limit_conn addr_conn 30;
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }
}
```

---

## 2. Production `Caddyfile` Alternative (Auto-HTTPS + HTTP/3)

```caddyfile
app.example.com {
    encode zstd gzip

    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server
    }

    request_body {
        max_size 20MB
    }

    reverse_proxy 127.0.0.1:3000 {
        health_uri /healthz
        health_interval 15s
        health_timeout 5s
    }
}
```
