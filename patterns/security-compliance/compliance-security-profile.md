# Compliance Security Profile for Regulated Workloads

**Category:** Security & Compliance

The regulatory frameworks that apply to the organization's data (HIPAA,
PCI-DSS, FedRAMP, and so on) are identified up front, and workspaces
that process that data run with the compliance security profile enabled
— before regulated data lands, not after.

## Why it matters

Regulatory alignment is usually asked as "are we compliant?", which the
platform alone can't answer. What the platform *can* do is provide the
technical controls a framework expects. On Databricks, that is the
compliance security profile, which supports standards including C5,
CCCS Medium, DoD IL5, FedRAMP High/Moderate, HIPAA, HITRUST, IRAP,
ISMAP, K-FSI, PCI-DSS, TISAX, and UK Cyber Essentials Plus.

Enabling it turns on:

- "Enhanced security monitoring, which includes monitoring agents that
  generate reviewable logs."
- "Automatic cluster updates, ensuring clusters have the latest updates
  by periodically restarting them during configurable maintenance
  windows."
- Hardened images (CIS Level 1, FIPS 140 validated), required instance
  types, and TLS 1.2+ for egress.

Ordering matters. Databricks is explicit that organizations are
responsible for verifying compliance and must configure the profile
*before* processing regulated data; HIPAA additionally requires a BAA in
place first. The profile carries an Enhanced Security and Compliance
add-on charge.

## What good looks like

- A written list of applicable frameworks per business domain, and a
  mapping from those to workspaces — so only the workspaces that need
  the profile pay for it.
- The profile enabled at the workspace (or account default) level for
  every workspace in scope, via IaC, with maintenance windows set
  deliberately.
- Enhanced security monitoring logs flowing into the same monitoring as
  the rest of the audit log — see
  [`security-audit-monitoring.md`](security-audit-monitoring.md).
- Supporting controls in place alongside it: sensitive-data
  classification ([`../unity-catalog-governance/automated-pii-classification.md`](../unity-catalog-governance/automated-pii-classification.md)),
  customer-managed keys where required
  ([`customer-managed-keys.md`](customer-managed-keys.md)), and a
  documented retention policy
  ([`../unity-catalog-governance/data-retention-policies.md`](../unity-catalog-governance/data-retention-policies.md)).
- This is a technical baseline, not a compliance audit — the library
  doesn't map controls to specific framework clauses.

## How to detect

Not in system tables. Read the workspace's enhanced security and
compliance settings through the Account / Workspace settings API (or
the account console): compliance security profile enabled, the listed
standards, enhanced security monitoring, and automatic cluster update.
The finding is a workspace holding data tagged for a regulated framework
(e.g. governed tags applied by data classification) whose profile is off.
`system.billing.usage` will show the add-on charge where it is enabled.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Compliance/regulatory alignment › Requirements for regulatory framework(s)?** — *primary.* Which frameworks apply (HIPAA, PCI-DSS, FedRAMP, GDPR...), and do in-scope workspaces run with the compliance security profile?
- **Security and Identity › CMEK** — *supporting;* primary pattern is [`customer-managed-keys.md`](customer-managed-keys.md).

## References

- [Compliance security profile](https://docs.databricks.com/aws/en/security/privacy/security-profile)
- [Configure enhanced security and compliance settings](https://docs.databricks.com/aws/en/security/privacy/enhanced-security-compliance)
- [Enhanced security monitoring](https://docs.databricks.com/aws/en/security/privacy/enhanced-security-monitoring)
