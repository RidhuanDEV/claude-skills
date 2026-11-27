# 06. AuthZ: RBAC, ABAC, ReBAC & Multi-Tenant Isolation

## 1. Purpose & Activation Conditions
Design server-enforced, deny-by-default authorization architectures (RBAC, ABAC, Zanzibar/OpenFGA ReBAC) that structurally prevent BOLA/IDOR, confused-deputy privilege escalation, mass assignment, and cross-tenant data leaks. Load when modeling permissions, multi-tenant queries, or document/workspace sharing hierarchies.

## 2. Prerequisites
- Verified canonical server principal (`userId`, `tenantId`, `roles`, `scopes`) derived strictly from authenticated session or verified token (`02`–`04`).

## 3. Technical Principles & Constraints
- **Deny-by-Default at Every Server Boundary:** UI route guards and hidden buttons are strictly UX convenience. Every REST controller, GraphQL resolver, server action, background export, and search endpoint MUST enforce server-side AuthN + AuthZ before touching data.
- **Zero-IDOR / Multi-Tenant Isolation Invariant:**
  - NEVER fetch, update, or delete multi-tenant resources by primary key alone (`WHERE id = $1`).
  - Always bind the authenticated caller's `tenant_id` directly inside the data query (`WHERE id = $1 AND tenant_id = $2`) AND layer PostgreSQL **Row-Level Security (`RLS`)** (`/shadow-db`) as defense-in-depth!
  - **Confused Deputy & Mass Assignment Ban:** NEVER accept `tenant_id`, `owner_id`, `role`, `permissions`, or `is_verified` from untrusted request bodies/queries/headers (`X-Tenant-Id`, `X-Role`, `X-Username`). Bind DTOs strictly through explicit field allowlists (`Zod`/`Pydantic`).
- **Choose the Right Authorization Model:**
  - **Tenant-Scoped RBAC (`Role -> Permission`):** Fine-grained permissions (`invoice:read:tenant`, `invoice:approve`, `user:manage`) checked via a centralized policy module instead of scattered `if (role === 'ADMIN')`.
  - **ABAC (Attribute-Based):** Adds resource/environment predicates (`amount <= approver_limit`, `resource.status === 'DRAFT'`, `resource.ownerId === actor.userId`).
  - **ReBAC (Zanzibar / OpenFGA / SpiceDB):** Required for deeply nested folder/document/org sharing graphs. **CRITICAL Consistency Rule:** Pass a **Zookie / consistency token** on reads immediately following permission revocation so stale replicas NEVER serve revoked data!
- **Status Concealment Semantics (`401` vs `403` vs `404`):** Return `401` when unauthenticated; return `403` for authenticated insufficient-role actions; preserve the owning service's established `403` refusal vs `404` concealment policy for cross-tenant object IDs (using `404` prevents confirming whether a guessed ID exists in another tenant).

## 4. Architecture & Implementation
```typescript
export type Permission =
  | 'invoice:read:own'
  | 'invoice:read:tenant'
  | 'invoice:approve'
  | 'tenant:export';

export interface AuthenticatedPrincipal {
  readonly userId: string;
  readonly tenantId: string;
  readonly role: 'viewer' | 'editor' | 'approver' | 'admin';
  readonly permissions: ReadonlySet<Permission>;
}

export interface InvoiceResource {
  readonly id: string;
  readonly tenantId: string;
  readonly ownerUserId: string;
  readonly status: 'draft' | 'pending_approval' | 'approved';
}

export function canPerformInvoiceAction(
  actor: AuthenticatedPrincipal,
  action: 'read' | 'approve',
  resource: InvoiceResource
): { readonly allowed: boolean; readonly httpStatus: 200 | 403 | 404; readonly reason: string } {
  // Hard tenant isolation boundary checked FIRST (conceal cross-tenant existence with 404 or 403 per service contract)
  if (actor.tenantId !== resource.tenantId) {
    return { allowed: false, httpStatus: 404, reason: 'cross_tenant_denied' };
  }
  if (action === 'read') {
    if (actor.permissions.has('invoice:read:tenant')) {
      return { allowed: true, httpStatus: 200, reason: 'tenant_read_granted' };
    }
    if (actor.permissions.has('invoice:read:own') && resource.ownerUserId === actor.userId) {
      return { allowed: true, httpStatus: 200, reason: 'owner_read_granted' };
    }
    return { allowed: false, httpStatus: 403, reason: 'missing_read_permission' };
  }
  if (action === 'approve') {
    if (!actor.permissions.has('invoice:approve')) {
      return { allowed: false, httpStatus: 403, reason: 'missing_approve_permission' };
    }
    // Maker-checker / ABAC invariant: creator cannot self-approve their own invoice
    if (resource.ownerUserId === actor.userId) {
      return { allowed: false, httpStatus: 403, reason: 'self_approval_forbidden' };
    }
    return { allowed: true, httpStatus: 200, reason: 'approval_granted' };
  }
  return { allowed: false, httpStatus: 403, reason: 'deny_by_default' };
}
```

## 5. Platform / Vendor Variations
| Authorization Need | Recommended Engine / Pattern | Key Operational Risk |
| :--- | :--- | :--- |
| **Standard SaaS Roles + Ownership** | Centralized TypeScript/Python/Go Policy Module + Postgres `WHERE tenant_id = $2` & RLS | Forgetting to call policy check on new secondary endpoints (exports, webhooks, GraphQL edges) |
| **Policy-as-Code Across Microservices** | OPA (Open Policy Agent) / Cedar | Policy bundle sync lag — pin policy revision & fail closed on OPA timeout |
| **Google-Drive-Style Nested Sharing** | OpenFGA / SpiceDB (Zanzibar ReBAC) | Stale read after revoke if Zookie/consistency token is omitted |

## 6. Decision Matrix & Trade-Offs
| Pattern | Granularity | Maintenance Overhead | Choose When |
| :--- | :---: | :---: | :--- |
| **RBAC + Tenant Scoping** | Medium | Low | 80% of B2B/B2C apps with clean role tiers |
| **RBAC + ABAC Predicates** | High | Low–Medium | Maker-checker, spend limits, record ownership, workflow states |
| **ReBAC (OpenFGA/SpiceDB)** | Very High | High | Multi-level folder/team/doc inheritance graphs |

## 7. Real Production Scenario
A multi-tenant billing API properly checks `tenant_id` on `GET /api/v1/invoices`, but a newly added `GET /api/v1/invoices/:id/pdf` download endpoint fetches `SELECT * FROM invoices WHERE id = $1` directly to save time. Any logged-in user in Tenant A who increments or guesses a UUID downloads Tenant B's confidential PDF invoices (`OWASP API1:2023 BOLA`). Moving all repository lookups to require `(id, actor.tenantId)` AND adding Postgres RLS + automated cross-tenant negative tests eliminates the entire bug class.

## 8. Failure Modes & Edge Cases
- **WRONG:** Checking authorization only in the API Gateway while an internal batch export worker or GraphQL nested resolver queries arbitrary `userId`/`tenantId` rows (Multi-Hop AuthZ / Confused Deputy!).
- **RIGHT:** Enforce tenant/permission predicates at the owning service/repository boundary AND propagate verified actor context into background jobs.
- **WRONG:** Passing `...req.body` directly into `prisma.user.update({ data: req.body })` allowing `{ "role": "admin", "tenantId": "other" }` mass assignment.
- **RIGHT:** Parse request bodies through strict explicit DTO schemas (`Zod`/`Pydantic`) that strip or reject unknown privileged fields.

## 9. Testing & Verification
- Run `python shadow-auth/scripts/auth_policy_verifier.py --check-policy-matrix <matrix.json>` and `python -m unittest discover -s shadow-auth/tests -v` (`test_auth_policy_matrix.py` runs the shipped policy gate offline: deny-by-default, tenant-scoped queries, required 401/cross-tenant/role-denial negative tests, session, JWT and SSO configs, and CLI exit codes; no HTTP server).
- Every new protected route PR MUST ship 3 negative tests: unauthenticated (`401`), cross-tenant access (`403`/`404`), and unauthorized role (`403`).

## 10. Operational Considerations
- Audit permission checks during every PR review by maintaining a machine-readable route-to-policy inventory so unprotected routes fail CI automatically.

## 11. Authoritative References
- OWASP API Security Top 10 (2023) — `API1:2023` (BOLA), `API3:2023` (BOPLA), `API5:2023` (BFLA) (`https://api-security.owasp.org/`).
- OWASP ASVS 5.0.0 — *V8 Authorization* (`https://github.com/OWASP/ASVS`).
- Pang et al. (USENIX ATC 2019) — *Zanzibar: Google's Consistent, Global Authorization System* (Zookie consistency).

## 12. Limitations & When NOT to Use
- Do NOT introduce OpenFGA/SpiceDB for a 3-role app (`admin`, `staff`, `viewer`) with flat tenant isolation — centralized tenant-scoped RBAC + ABAC + Postgres RLS is simpler, faster, and easier to audit.
