# 05 — Kubernetes (K8s), Helm & Terraform / OpenTofu Infrastructure-as-Code

Pair with [`vendor/OWASP_Kubernetes_Security_Cheat_Sheet.md`](vendor/OWASP_Kubernetes_Security_Cheat_Sheet.md).

---

## 1. Production Kubernetes Manifest Bundle (`Deployment` + `PDB` + `HPA` + `NetworkPolicy`)

Every production Kubernetes workload MUST define:
- Separate `startupProbe`, `livenessProbe` (process-only, NEVER querying external DB), and `readinessProbe` (checks DB/Redis readiness).
- `preStop` lifecycle hook (`sleep 5`) + `terminationGracePeriodSeconds: 30` so kube-proxy/Ingress drains in-flight requests before `SIGTERM`.
- Strict `securityContext` (`runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`).
- `PodDisruptionBudget` (`minAvailable: 1`) and `HorizontalPodAutoscaler`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: prod
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: api
          image: registry.example.com/app/api:v1.2.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 3000
              name: http
          envFrom:
            - secretRef:
                name: api-env-secrets
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              memory: "512Mi"
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            failureThreshold: 15
            periodSeconds: 2
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 15
            timeoutSeconds: 3
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 2
          volumeMounts:
            - name: tmp-dir
              mountPath: /tmp
      volumes:
        - name: tmp-dir
          emptyDir: {}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: prod
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api-server
```

---

## 2. Terraform / OpenTofu Module Hygiene

- Always separate `versions.tf`, `variables.tf`, `main.tf`, and `outputs.tf`.
- Enforce remote state locking (S3 + DynamoDB or GCS) and set `lifecycle { prevent_destroy = true }` on stateful databases and storage buckets.
