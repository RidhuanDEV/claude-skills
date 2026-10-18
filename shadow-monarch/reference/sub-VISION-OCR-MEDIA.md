# sub-VISION-OCR-MEDIA — Computer Vision, Document OCR, Speech/Audio & `ffmpeg` Pipelines

Use when building OCR pipelines (e-KTP, NPWP, invoices, scanned PDFs), image/video Computer Vision inference (YOLO,
OpenCV, ONNX Runtime, face verification/liveness), Speech-to-Text / Text-to-Speech (Whisper, audio streaming), or
automated media processing with `ffmpeg` / `sharp`.

## 1. Image pre-processing & upload hygiene

Before feeding any user-uploaded image into OCR, Vision LLMs, or object detection:
- **Validate magic bytes & strip dangerous metadata**: verify actual file signature (`image/jpeg`, `image/png`, `image/webp`,
  `application/pdf`), enforce max pixel dimensions (prevent decompression bombs, e.g., $10000 \times 10000$ px), and
  **auto-rotate based on EXIF Orientation tag** before stripping EXIF GPS/camera metadata (`sharp(buf).rotate()`).
  *(Unrotated mobile photos upside-down or $90^\circ$ sideways cause catastrophic OCR/detection accuracy drops.)*
- **Aspect-ratio safe resizing**: use **letterboxing / padding** when resizing for fixed-square YOLO/ONNX tensors
  (e.g., $640 \times 640$) rather than stretching the image, and map bounding-box coordinates back to the original image dimensions.

## 2. Document AI & OCR pipelines (e-KTP, Invoices, Tables, Scanned PDFs)

- **Hybrid extraction strategy**:
  1. Check if the PDF already contains a digital text layer (`pdfplumber` / `PyMuPDF` / `pdfjs-dist`). Only run OCR on
     pages where digital text is empty or garbled.
  2. For scanned pages or ID cards: run deskewing, contrast normalization / adaptive thresholding, and layout detection
     (`PaddleOCR` / `Surya` / `Tesseract` / Vision LLM).
- **Structured validation & Confidence Gating**:
  - Parse extracted fields through a strict schema (e.g., Indonesian NIK = 16 digits with valid province/district/DOB prefix,
    invoice line items `sum(qty * unit_price) == subtotal`).
  - Attach a **per-field confidence score** or validation status (`VERIFIED`, `LOW_CONFIDENCE_NEEDS_REVIEW`, `INVALID_CHECKSUM`).
  - Route low-confidence or mathematically inconsistent extractions to a **Human-in-the-Loop (HITL) review UI** showing the
    cropped bounding box next to the editable form field.

## 3. Computer Vision inference (ONNX Runtime, OpenCV, YOLO, Biometrics)

- **Color channel discipline**: OpenCV (`cv2.imread`) loads images in **`BGR`** order, whereas PIL, PyTorch, TensorFlow,
  and most ONNX models expect **`RGB`**. Always convert explicitly (`cv2.cvtColor(img, cv2.COLOR_BGR2RGB)`).
- **Non-blocking inference**:
  - Never run CPU/GPU tensor inference directly on the main Node.js event loop or Python `asyncio` loop. Offload to a
    dedicated worker pool (`ProcessPoolExecutor`, Triton/ONNX server, or queue worker) with bounded batch size and request timeout.
  - Warm up the model with a dummy tensor at worker startup so the first real user request does not pay cold-start JIT/CUDA allocation latency.
- **Face Verification & Liveness (Anti-Spoofing)**:
  - Never rely on 2D face cosine similarity alone for identity verification (easily spoofed with a printed photo or phone screen).
  - Require passive/active liveness detection, rate-limit verification attempts, and store only encrypted/irreversible
    feature embeddings (biometric templates are Specific Personal Data under UU PDP).

## 4. Audio, Speech (Whisper / TTS) & `ffmpeg` rules

- **Safe `ffmpeg` execution (zero shell injection)**:
  - **NEVER** pass user filenames or URLs into a shell string `exec("ffmpeg -i " + userInput)`. Always spawn `ffmpeg`
    with an **argument array** (`spawn('ffmpeg', ['-nostdin', '-y', '-i', inputPath, ...])`) and forbid untrusted remote URLs/protocols (`-protocol_whitelist file,pipe`).
- **Web-ready video & audio flags**:
  - MP4 for web streaming: `-c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart`
    (`+faststart` moves the `moov` atom to the front so playback starts immediately before full download).
  - Audio normalization for Speech-to-Text (`Whisper`): resample to **16 kHz mono PCM WAV** (`-ar 16000 -ac 1 -c:a pcm_s16le`)
    and apply Voice Activity Detection (**VAD** like `silero-vad`) to strip long silences (prevents Whisper hallucination loops on silent segments).
