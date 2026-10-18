# sub-AI-INFRA-SERVING — GPU Infrastructure, vLLM/TGI/Ollama Serving, Quantization & LLM Gateways

Use when sizing GPU hardware, self-hosting open-weight LLMs/Embedding/Reranker models (`vLLM`, `SGLang`, `TGI`,
`TensorRT-LLM`, `Triton`, `llama.cpp`, `Ollama`), configuring Kubernetes GPU clusters, or deploying LLM Gateways (`LiteLLM`, `Portkey`, `Envoy AI Gateway`).

## 1. GPU VRAM Sizing & Memory Math (Non-Negotiable Calculation)

Never guess GPU specs for LLM serving. Calculate total VRAM from the 3 memory components:
$$\text{VRAM}_{\text{total}} = \text{VRAM}_{\text{weights}} + \text{VRAM}_{\text{KV-cache}} + \text{VRAM}_{\text{activations & CUDA overhead } (\approx 10\%\text{--}15\%)}$$

1. **Model Weights ($\text{VRAM}_{\text{weights}}$)**:
   - **FP16 / BF16**: $\approx 2 \text{ bytes} \times \text{Parameters}$ (e.g., $7\text{B} \approx 14\text{ GB}$, $32\text{B} \approx 64\text{ GB}$, $70\text{B} \approx 140\text{ GB}$).
   - **FP8 / INT8** (W8A8 / Hopper/Ada GPUs: H100, L40S, L4, RTX 4090): $\approx 1 \text{ byte} \times \text{Parameters}$ ($70\text{B} \approx 70\text{ GB}$).
   - **INT4 Quantization (`AWQ`, `GPTQ`, `GGUF Q4_K_M`)**: $\approx 0.55\text{--}0.6 \text{ bytes} \times \text{Parameters}$ ($8\text{B} \approx 5\text{ GB}$, $70\text{B} \approx 40\text{ GB}$).
2. **KV-Cache ($\text{VRAM}_{\text{KV-cache}}$) for Concurrent Requests**:
   $$\text{Bytes per Token} = 2 \ (\text{K and V}) \times n_{\text{layers}} \times n_{\text{kv\_heads}} \times d_{\text{head}} \times \text{bytes\_per\_elem}$$
   $$\text{VRAM}_{\text{KV-cache}} = \text{Bytes per Token} \times \text{Max Concurrent Tokens } (\text{Batch Size} \times \text{Context Length})$$
   - Models with **GQA (Grouped-Query Attention)** (Llama-3, Qwen-2.5/3, Mistral) use $4\times\text{--}8\times$ less KV-cache than legacy MHA models.
   - Always cap `--max-model-len` to the actual context length your application needs (e.g., `8192` or `16384`, not `131072` if unused) so vLLM reserves VRAM for higher batch concurrency!
3. **Bandwidth determines token generation speed (ITL — Inter-Token Latency)**:
   - Decoding is **memory-bandwidth bound**: $\text{Max Single-Stream Tokens/sec} \approx \frac{\text{GPU Memory Bandwidth (GB/s)}}{\text{VRAM}_{\text{weights}}\text{ (GB)}}$.

## 2. Production LLM Serving with `vLLM` & `SGLang`

- **Use `vLLM` or `SGLang` for multi-user production APIs** (Continuous Batching + PagedAttention/RadixAttention yield $5\times\text{--}20\times$ higher throughput than naive HuggingFace `pipeline()` or single-stream `Ollama` defaults).
- **Essential `vLLM` production flags**:
  ```bash
  vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ \
    --quantization awq_marlin \
    --tensor-parallel-size 2 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.90 \
    --enable-prefix-caching \
    --max-num-seqs 128 \
    --guided-decoding-backend xgrammar \
    --disable-log-requests
  ```
- **Multi-GPU parallelism rules**:
  - **Tensor Parallelism (`--tensor-parallel-size N`, TP)**: splits single layers across GPUs on the **same node** (requires high-speed NVLink/PCIe P2P; set `N` to a power of 2 that divides `n_kv_heads`, e.g., 2, 4, or 8).
  - **Data Parallelism (Replicas)**: if a model fits on 1 GPU (e.g., 8B BF16 or 32B AWQ on 1× A100/H100 80GB), run **multiple independent 1-GPU replicas** behind a load balancer rather than 1 TP=4 instance — replicas scale linearly without inter-GPU communication overhead!
- **Co-hosting Embedding & Reranker models**: serve embeddings (`BGE-M3`) and cross-encoder rerankers on dedicated **`Text Embeddings Inference (TEI)`** or **`Infinity`** containers (or separate GPU MIG slices / CPU-AVX512 nodes) so heavy embedding batches never starve LLM token generation latency.

## 3. Kubernetes (K8s) GPU Orchestration & Autoscaling

- **Never bake multi-gigabyte model weights into Docker container images**:
  - Mount a pre-populated ReadOnlyMany PVC (NVMe/FSx/Filestore) or S3/MinIO object cache synced via an `initContainer` (`HF_HOME=/models`) so pod restarts take seconds, not 20 minutes of image pulls.
- **GPU Pod manifest requirements**:
  - Request and limit `nvidia.com/gpu: 1` (or $N$ for TP). Set `ipc: host` or mount a memory-backed `emptyDir` (`medium: Memory`, `sizeLimit: 16Gi`) at `/dev/shm` — **PyTorch NCCL multi-GPU Tensor Parallelism crashes if `/dev/shm` defaults to 64MB!**
  - Configure `startupProbe` with a generous threshold (`failureThreshold: 60`, `periodSeconds: 10` = 10 min) to allow weight loading and CUDA graph compilation before `livenessProbe` starts.
- **Autoscaling (KEDA + Prometheus)**:
  - **Never autoscale LLM pods on CPU%** (GPU pods sit at low CPU while GPU KV-cache is 100% saturated).
  - Autoscale on `vllm:num_requests_waiting` (queue depth $> 5$) and `vllm:gpu_cache_usage_perc` ($> 0.80$), with scale-down stabilization windows ($\ge 10\text{--}15\text{ minutes}$) to avoid thrashing expensive GPU cold starts.

## 4. LLM Gateway / AI Proxy Architecture (`LiteLLM` / `Portkey` / `Envoy AI Gateway`)

Place a centralized LLM Gateway between application services and model providers (Cloud APIs + Self-Hosted vLLM):
- **Unified OpenAI-compatible contract**: app code calls one internal gateway URL using logical model aliases (`model: "tier-1-fast"`, `"tier-2-rag"`, `"embedding-default"`). Swapping providers or upgrading models requires zero application code redeploy.
- **Traffic management & reliability**:
  - Prefix-aware / KV-cache-aware routing for self-hosted vLLM replicas (route conversations sharing the same system/RAG prefix to the same replica to maximize KV-cache hits).
  - Automatic health checks, circuit breaking, and cross-provider fallbacks (e.g., Self-hosted vLLM saturated → burst overflow to Cloud API).
- **Governance & multi-tenant cost control**:
  - Issue Virtual API Keys per service/team/tenant with hard **RPM (Requests/Min)**, **TPM (Tokens/Min)**, and **Monthly USD Spend Limits**.
  - Centralized PII masking, prompt-injection guardrails, semantic caching (Redis), and OpenTelemetry trace export to Langfuse/Phoenix.

## 5. Local / Edge Serving (`Ollama` & `llama.cpp`)

- When deploying on developer workstations or edge appliances with `Ollama` / `llama-server`:
  - Explicitly set `OLLAMA_NUM_PARALLEL` (default 1–4), `OLLAMA_MAX_LOADED_MODELS` (prevent VRAM thrashing from model swapping), `OLLAMA_FLASH_ATTENTION=1`, and `OLLAMA_KV_CACHE_TYPE=q8_0` (halves KV-cache VRAM with negligible quality loss).
  - Always pass `num_ctx` explicitly in API requests (`Ollama` defaults to `2048` or `4096` tokens if omitted, silently truncating long RAG prompts!).
