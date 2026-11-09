# 03 — Linux SysAdmin, `systemd`, PM2, Firewall & VPS Kernel Tuning

---

## 1. Hardened `systemd` Service Unit (`/etc/systemd/system/app.service`)

Use for Go, Rust, Python (`gunicorn`/`uvicorn`), Node, or Java services running directly on a Linux VPS:

```ini
[Unit]
Description=Production Backend Service
After=network-online.target postgresql.service redis.service
Wants=network-online.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/srv/app
EnvironmentFile=/srv/app/.env.production
ExecStart=/srv/app/bin/server
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60
StartLimitBurst=5
TimeoutStopSec=30s
KillMode=mixed
KillSignal=SIGTERM

# Resource & File Descriptor Limits
LimitNOFILE=65535
MemoryMax=2G

# Security Sandboxing
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/srv/app/storage /var/log/app
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
```

---

## 2. PM2 Production Ecosystem (`ecosystem.config.cjs`)

When managing Node.js clusters via PM2 on VPS:
- Always use `exec_mode: "cluster"` with `instances: "max"` (or CPU count) for stateless HTTP APIs, and `exec_mode: "fork"` with `instances: 1` for cron/queue workers so jobs are not duplicated!
- Configure `max_memory_restart`, `kill_timeout`, and `wait_ready: true` for zero-downtime `pm2 reload`.

```javascript
module.exports = {
  apps: [
    {
      name: "api-server",
      script: "./dist/main.js",
      instances: 2,
      exec_mode: "cluster",
      max_memory_restart: "750M",
      kill_timeout: 15000,
      wait_ready: true,
      listen_timeout: 10000,
      env_production: {
        NODE_ENV: "production",
        PORT: 3000,
      },
      error_file: "/var/log/app/api-error.log",
      out_file: "/var/log/app/api-out.log",
      merge_logs: true,
      time: true,
    },
    {
      name: "queue-worker",
      script: "./dist/worker.js",
      instances: 1,
      exec_mode: "fork",
      max_memory_restart: "512M",
      kill_timeout: 30000,
      env_production: {
        NODE_ENV: "production",
      },
    },
  ],
};
```

---

## 3. VPS Host Hardening, `logrotate` & Kernel `sysctl` Tuning

### A. Firewall (`ufw`) & SSH Baseline
```bash
# Default deny incoming, allow only SSH (or custom port / Tailscale) + HTTP/HTTPS
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable
```

### B. `/etc/sysctl.d/99-production-tuning.conf` (High-Concurrency & Redis Safety)
```ini
# Prevent Redis background save fork failure
vm.overcommit_memory = 1
vm.swappiness = 10

# Increase file descriptors & TCP backlog for high RPS
fs.file-max = 2097152
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 10240 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
```

### C. `/etc/logrotate.d/app` (Prevent 100% Disk Full Outages)
```text
/var/log/app/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 appuser adm
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
```
