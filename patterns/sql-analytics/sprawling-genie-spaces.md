# Sprawling Genie Spaces

> ⚠️ **ANTI-PATTERN**

**Category:** SQL & Analytics

One Genie space is pointed at dozens of tables across several domains
and expected to answer anything anyone asks — with guidance supplied as
long paragraphs of text instructions rather than SQL — so its answers
are plausible, inconsistent, and hard to trust.

## Why it happens

A Genie space that covers everything looks strictly better than one
that covers a topic. Adding a table costs nothing at setup time, and
each addition is justified by a real question someone asked. The table
count grows toward the 50-table ceiling one reasonable request at a
time.

Text instructions accumulate the same way. When an answer comes back
wrong, the fastest fix is to write a sentence telling Genie not to do
that. Twenty incidents later there are twenty sentences, some of which
now contradict each other, and no one can tell which one is causing the
current behavior.

## Impact

- Accuracy degrades with scope. Databricks' guidance is to aim for
  **five or fewer tables** and that "the more focused your selection,
  the better" — a space near the ceiling is operating far outside
  where it performs well.
- Conflicting instructions produce unpredictable output, which is why
  the guidance explicitly says to "avoid conflicting guidance across
  instruction types."
- Text instructions are the weakest lever available. The recommended
  hierarchy is SQL expressions first, example queries second, and text
  "only when SQL methods [are] insufficient" — a space built mostly on
  prose has skipped the two mechanisms that actually constrain
  behavior.
- No audience means no evaluable quality bar: an agent "should answer
  questions for a particular topic and audience, not general questions
  across various domains," and without that, benchmark questions cannot
  be written.
- Users lose trust after a few confidently wrong answers, and trust
  does not come back when the space is later fixed.

## How to fix

1. Split by topic and audience. Several focused spaces outperform one
   general one, and each becomes independently testable.
2. Reduce each space toward five tables. Where a topic genuinely needs
   more, "prejoin related tables into views or metric views before
   adding them" rather than adding raw tables.
3. Convert text instructions into SQL expressions for metrics, filters,
   and dimensions, and into example SQL queries for complex multi-part
   logic. Delete the prose those replace instead of leaving both.
4. Add trusted assets for the recurring questions the space exists to
   answer, so anticipated questions get verified answers.
5. Write benchmark questions and score them, so the next change is
   evaluated rather than hoped for. See
   [`curated-genie-spaces.md`](curated-genie-spaces.md).
6. Fix the underlying metadata — column names and comments — since no
   amount of instruction compensates for tables Genie cannot interpret.
7. Put the space in a bundle so its configuration is versioned and
   changes are reviewable.

## How to detect

The Genie API exposes each space's table list, instruction set, and
trusted assets: table count well above five (and approaching 50),
instruction text dominated by prose, and zero trusted assets are the
three direct findings. Tables spanning unrelated schemas in one space
indicates missing topic boundaries. The Monitoring tab shows question
volume and user feedback; `system.query.history` and
`system.access.audit` show the queries the space actually issues, which
is how you tell whether it is answering its intended topic or being
used as a general-purpose search box.

## References

- [Curate an effective Genie Agent](https://docs.databricks.com/aws/en/genie/best-practices)
- [Use trusted assets in AI/BI Genie spaces](https://docs.databricks.com/aws/en/genie/trusted-assets)
- [Unity Catalog metric views](https://docs.databricks.com/aws/en/uc-semantics/metric-views/)
