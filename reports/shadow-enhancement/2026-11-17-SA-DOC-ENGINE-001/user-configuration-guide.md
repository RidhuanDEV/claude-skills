# SA-DOC-ENGINE-001 — User Configuration Guide

## 1. Optional Project Configuration (`.shadow/document-engine.json` or `shadow-doc.config.json`)

Place configuration inside the **target project root** using platform-independent relative paths or environment variables (never hardcode global IDE config edits without permission):

```json
{
  "schemaVersion": "1.0.0",
  "documentGeneration": {
    "mode": "auto",
    "preferredGenerator": "project-first",
    "projectGenerator": {
      "id": "custom-repo-docs",
      "name": "Project Document Script",
      "entry": "./tools/build_docs.py",
      "supportedInputs": ["markdown", "json"],
      "supportedOutputs": ["docx", "pdf", "html"],
      "templateDir": "./templates",
      "inputDir": "./docs",
      "outputDir": "./dist/docs",
      "tempDir": "./.shadow/tmp"
    },
    "globalEngine": {
      "path": "${SHADOW_DOC_HOME}/scripts/doc_scaffold.py",
      "version": "2.1.0"
    },
    "output": {
      "strategy": "project-local",
      "overwrite": false
    }
  }
}
```

## 2. CLI Commands (`doc_orchestrator.py` & `doc_scaffold.py`)

```powershell
# Discover generators in current repo
python "shadow-doc/scripts/doc_scaffold.py" discover --repo .

# Resolve best generator for target formats
python "shadow-doc/scripts/doc_scaffold.py" resolve --repo . --outputs docx,html,pdf

# Safe export (fails if file exists unless --overwrite is explicitly added)
python "shadow-doc/scripts/doc_scaffold.py" export --doc docs/SRS.json --format md,html,docx,pdf,xlsx --out-dir docs/output --allowed-root .
```
