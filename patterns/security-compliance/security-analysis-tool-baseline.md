# Security Posture Baseline with the Security Analysis Tool

**Category:** Security & Compliance

Account and workspace security configuration is checked continuously
against Databricks' published best practices using the Security
Analysis Tool (SAT), with the results tracked over time — instead of a
one-off checklist completed at go-live.

## Why it matters

Most of the security surface — network configuration, token policy,
IP access lists, admin counts, encryption settings — is exposed through
account and workspace APIs, not system tables. That makes it invisible
to SQL-based assessments and easy to drift silently after launch.

SAT is "an observability utility designed to improve the security
posture of Databricks deployments." It evaluates over 65 security
controls across five areas — Network Security, Identity & Access, Data
Protection, Governance, and Informational — classifies findings as High,
Medium, or Low severity, and runs "as an automated daily workflow"
inside your own environment, storing results in Delta tables for trend
analysis. It supports AWS, Azure, and GCP, with "a small number of
checks" limited to clouds where the underlying API exists.

For an assessment, SAT is the fastest way to cover the security
questions this library otherwise marks NOT_AVAILABLE.

## What good looks like

- SAT deployed once per account (it can scan many workspaces), running
  on a schedule under a service principal with the minimum permissions
  its setup guide lists.
- Results reviewed through its dashboards — the detailed dashboard for
  the platform team, the executive summary for leadership — with High
  severity findings tracked to closure.
- Accepted risks documented explicitly, so a recurring finding has an
  owner and a reason rather than becoming background noise.
- Trend matters more than the snapshot: the number of High findings
  should fall over time, and a new one appearing should raise an alert.
- SAT complements, not replaces,
  [`security-audit-monitoring.md`](security-audit-monitoring.md): SAT
  says how things are configured; the audit log says who changed them.

## How to detect

Check whether SAT is installed: a job or bundle deployment for it in
`system.lakeflow.jobs` (job names from the SAT installer), and its
output schema/tables in `system.information_schema.tables`. Recent
successful runs in `system.lakeflow.job_run_timeline` show it is
current. If it isn't installed, running SAT is itself the recommended
first step of the security portion of the assessment.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Security and Identity › SSO and identity management** — *supporting;* primary pattern is [`account-first-identity-federation.md`](../platform-onboarding/account-first-identity-federation.md).
- **Security and Identity › Secrets** — *supporting;* primary pattern is [`secrets-management.md`](secrets-management.md).

## References

- [Security Analysis Tool (GitHub)](https://github.com/databricks-industry-solutions/security-analysis-tool)
- [SAT functionality](https://databricks-industry-solutions.github.io/security-analysis-tool/docs/functionality/)
- [SAT installation](https://databricks-industry-solutions.github.io/security-analysis-tool/docs/installation/)
