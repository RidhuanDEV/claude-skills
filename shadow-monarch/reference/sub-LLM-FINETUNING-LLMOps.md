# sub-LLM-FINETUNING-LLMOps — Fine-Tuning (LoRA/QLoRA/DPO), Dataset Curation, Guardrails & LLMOps

Use when deciding between RAG and Fine-Tuning, curating instruction/preference datasets, training open-weight LLMs
(Unsloth, Axolotl, LLaMA-Factory, HuggingFace `trl`), deploying multi-LoRA adapters, or building LLMOps evaluation
and guardrail pipelines (`Langfuse`, `Arize Phoenix`, `Promptfoo`, `DeepEval`, `Llama Guard`).

## 1. Decision framework: Prompt Engineering vs RAG vs Fine-Tuning

Never fine-tune an LLM to teach it rapidly changing facts:
| Goal / Problem | Right Solution | Why |
|---|---|---|
| Model lacks access to private/current company documents | **RAG (`sub-RAG-VECTOR-KNOWLEDGE.md`)** | Facts change daily; RAG provides citations, instant updates, and RBAC filtering. |
| Model fails to follow complex instructions or output format | **Structured Outputs + Few-Shot Prompting** | Fastest iteration; zero training infra. |
| Frontier model works well, but is too slow or expensive at scale | **Knowledge Distillation + Fine-Tuning (SFT)** | Train a smaller 3B–8B model on verified inputs/outputs from the 70B/frontier teacher. |
| Need consistent domain tone, specialized DSL/SQL dialect, or compact prompt | **LoRA / QLoRA Fine-Tuning (SFT)** | Bakes behavioral rules and domain syntax into weights, eliminating 4,000-token system prompts. |
| Model generates plausible text but makes subtle preference/reasoning mistakes | **DPO / ORPO / GRPO Alignment** | Aligns model probabilities using `<prompt, chosen, rejected>` pairs or verifiable reward functions. |

## 2. Dataset curation & hygiene (80% of fine-tuning success)

1,000 pristine, diverse, verified examples beat 100,000 noisy scraped examples:
- **Standard chat format (ChatML / OpenAI `messages` JSONL)**:
  - Ensure training chat templates (`<|im_start|>`, `<|begin_of_text|>`) match the base model's exact tokenizer `chat_template` — a single mismatched special token or EOS token causes infinite generation loops at inference!
- **Data quality pipeline**:
  1. **Schema & syntax verification**: if training for SQL, code, or JSON tool calls, execute/validate every single target completion in the training set before training.
  2. **Deduplication & diversity**: deduplicate near-identical prompts using MinHash LSH or embedding cosine similarity ($> 0.92$).
  3. **Decontamination**: ensure zero overlap between training examples and your evaluation golden set.
  4. **PII & secret scrubbing**: strip real customer PII, API keys, and internal credentials from training corpora (models memorize and regurgitate rare strings).
  5. **Refusal & negative examples**: include 5%–10% out-of-scope or adversarial examples where the target completion is a clean refusal or *"Not found in context"* so the fine-tuned model does not lose safety boundaries or hallucinate when context is missing (**RAFT — Retrieval-Augmented Fine-Tuning** pattern).

## 3. LoRA / QLoRA (SFT) & Post-Training Alignment rules

- **Hyperparameter baseline (`Unsloth` / `Axolotl` / `LLaMA-Factory` / `TRL SFTTrainer`)**:
  - **Target modules**: apply LoRA to **all linear layers** (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`), not just `q_proj`/`v_proj` — matches full fine-tuning quality closely.
  - **Rank (`r`) & Alpha (`lora_alpha`)**: `r = 16` or `32` (use `64` for complex domain adaptation), `lora_alpha = r` or `2 * r`, `lora_dropout = 0.0` (for Unsloth fast kernels) or `0.05`.
  - **Loss masking (`train_on_inputs = False` / `DataCollatorForCompletionOnlyLM`)**: compute cross-entropy loss **only on assistant response tokens**, never on system/user prompt tokens.
  - **Learning rate & epochs**: `lr = 1e-4` to `2e-4` for LoRA (`5e-6` to `5e-5` for DPO), cosine scheduler with `5%–10%` warmup, `bf16 = True` (never `fp16` on Ampere+ GPUs due to overflow), `2–3 epochs` max (watch validation loss to stop before overfitting).
- **Multi-LoRA serving in production**:
  - Instead of merging 10 separate 16GB models for 10 specialized tasks/tenants, deploy **1 shared base model in `vLLM` (`--enable-lora --max-loras 8`)** and dynamically route requests to lightweight ~100MB LoRA adapter weights per `model` name!

## 4. Guardrails, Safety & Output Verification

Implement fast, deterministic or lightweight-classifier guardrails around the LLM:
- **Input Guardrails (Pre-LLM)**:
  - Prompt injection & jailbreak classifier (`Llama-Guard-3`, `Prompt-Guard`, `Lakera` / `NeMo Guardrails`).
  - PII detection & tokenization (Microsoft `Presidio` + Indonesian regex for 16-digit NIK, NPWP, phone numbers, bank accounts): replace PII with placeholders (`<PERSON_1>`, `<NIK_1>`) before calling external LLM APIs, and re-hydrate locally if authorized.
- **Output Guardrails (Post-LLM)**:
  - Schema & business invariant validator (e.g., verify generated SQL is read-only `SELECT` via AST parser `sqlglot` before execution; verify cited document IDs actually exist in the retrieved context set; verify recommended product IDs are in stock).

## 5. LLMOps: Tracing, Evaluation & Continuous Regression (`Langfuse` / `Phoenix` / `Promptfoo`)

- **OpenTelemetry GenAI Tracing**:
  - Instrument every pipeline run with hierarchical spans: `Trace (User Request)` → `Span (Query Rewrite)` → `Span (Hybrid Retrieval + Rerank)` → `Generation Span (LLM Call: prompt_name, prompt_version, model, temperature, input/output tokens, cost)` → `Span (Guardrail/Validator)`.
- **Three-tier Evaluation Pipeline**:
  1. **Offline CI Gate (`Promptfoo` / `DeepEval` / `pytest`)**: run 50–200 golden-set test cases on every PR that touches prompts, RAG chunking, or model versions. Assert 100% pass on deterministic checks (JSON schema, no PII leak, injection refusal) and non-regression on rubric scores.
  2. **LLM-as-a-Judge calibration**: use a strong reasoning model with a **binary or 1–5 integer rubric + chain-of-thought explanation**, and measure judge agreement (Cohen's Kappa) against a small human-graded sample.
  3. **Online Production Monitoring & Flywheel**: sample 1%–5% of production traces for async quality scoring; automatically route thumbs-down user feedback, guardrail triggers, and schema-retry failures into an annotation queue to grow the golden evaluation and fine-tuning dataset.
