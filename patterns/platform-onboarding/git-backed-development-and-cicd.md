# Git-Backed Development and CI/CD

**Category:** Platform Onboarding

All notebooks, source files, and bundle configuration live in a Git
repository; work happens on short-lived branches and reaches production
only through an automated pipeline — never by editing a notebook in the
production workspace.

## Why it matters

Databricks' developer guidance is to "version control all files" —
notebooks, `.py`/`.sql` source, and `databricks.yml` — while excluding
build artifacts, credentials, and PII. It goes further and recommends
"a single repository for all of your code," on the grounds that
cross-team visibility beats per-team repo isolation for a data
platform, where the interesting bugs are usually at the seams.

The branching guidance is trunk-based: short-lived feature branches,
synced regularly, merged into main only after testing, then promoted to
staging and production by automated CI/CD. The operational-excellence
pillar makes the same point from the other direction — CI/CD makes
releases "more frequent and reliable" than manual promotion.

For a team onboarding onto Databricks, this is the practice most likely
to be skipped, because the workspace UI makes editing production
notebooks so easy. See
[`notebooks-as-production-code.md`](notebooks-as-production-code.md).

## What good looks like

- Databricks Git folders (or VS Code with the Databricks extension) as
  the development surface — so the workspace is a view onto the repo,
  not a separate copy of the truth.
- Trunk-based flow: feature branch → tested merge to main → automated
  promotion. Hotfixes are used sparingly and merged back to main
  immediately.
- Core business logic lives in importable `.py` modules and `.sql`
  files; notebooks are used for orchestration and visualization, not as
  the home of the logic.
- No hardcoded environment variables between tasks — use dynamic
  references like `{{tasks.<task_key>.values.<value_key>}}`.
- Table and column comments are treated as code: maintained in `.sql`
  files and deployed by a metadata job, not typed into the UI.
- Three testing layers: unit tests with pytest, `bundle validate`, and
  integration tests in staging before production promotion.
- Deployment runs as a service principal distinct from the runtime
  principal — see
  [`service-principals-for-automation.md`](service-principals-for-automation.md).

## How to detect

Git linkage isn't in system tables. The realistic checks are on the
repo side (does every deployed job have a corresponding definition in
version control?) and on the workspace side via the Workspace API,
which reports whether a notebook path sits inside a Git folder. The
system-table proxy is authorship churn: `system.access.audit` records
`workspace` service events such as notebook edits in production
workspaces, and a production workspace where notebooks are being
edited interactively is the signal this pattern is missing.

## References

- [Developer best practices on Databricks](https://docs.databricks.com/aws/en/developers/best-practices)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
- [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)
