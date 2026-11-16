# SBOM Risk Register & Release Attestation Playbook

```yaml
manifest_id: "SC-0001"
lockfile_synced: true
lockfile_packages:
  - { name: "express", version: "4.21.2", scope: "runtime" }
sbom_components:
  - { name: "express", version: "4.21.2", license: "MIT" }
ci_actions:
  - "actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11"
container_base: "node:22-alpine@sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
provenance:
  signer_verified: true
  slsa_level: "SLSA_BUILD_L2"
waivers: []
```
