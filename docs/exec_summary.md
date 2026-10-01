# Executive Summary
## Apple Retail Sales - Data Quality & Reconciliation

**Date:** 2026-09-30 | **Author:** [Walid_Chibi]

**Headline.** Five retail sources totalling 1,070,374 records - including 1,040,200 sales rows - were audited with 96 automated checks before any cleaning. Six defect classes were found; the largest is systemic: 493,143 sales (47.4%) are dated before their product's launch, and those rows carry 45.97% of $6.17B gross revenue. Every defect was dispositioned under a versioned rules contract (FIX / FLAG / QUARANTINE - never delete), and the pipeline reconciles rows, units and revenue to $0.00 unexplained variance - verified by four independent engines: two pandas implementations, MySQL SQL audits, and a Power Query port.

**Objective.** Prove the multi-source data can be trusted before BI migration: audit all five tables, profile the damage, clean under a logged contract, reconcile revenue to the unit across the pipeline, and deliver a clean relational model ready for BI.

**Method - five stages, each independently verified.**

1. **Profile.** 96 checks (identity, completeness, conformity, referential, domain, temporal, duplicates) produced a damage report; ten written assumptions were adjudicated against evidence - two were violated, eight confirmed.
2. **Contract.** Every finding became a versioned rule with evidence and disposition. One pre-drafted rule was deliberately dropped when the value census proved the defect did not exist - profiling prevented a fix for a non-existent problem.
3. **Clean.** The engine reads the contract; outputs are clean parquet, a quarantine area, and a per-rule audit log. Engine counts are cross-checked against profiler counts before anything ships.
4. **Reconcile.** An independent ledger recomputes raw vs clean vs quarantined for rows, units and revenue; non-zero variance halts the pipeline with a non-zero exit code.
5. **Enforce & serve.** MySQL dual schema - all-VARCHAR raw vs typed clean under PK/FK/CHECK enforcement - plus a before/after audit scorecard and star-schema BI views with contract flags exposed as one-click filters.

**Findings and business impact.**

| Finding | Scale | Disposition | Business impact |
|---|---|---|---|
| Sales dated before product launch | 493,143 rows (47.4%) - 45.97% of $6.17B | Flag & retain | Pre-launch semantics must be settled with the source owner before any launch-based KPI is published; BI ships a one-click exclude. |
| Warranty claims before their sale | 2,687 (9.0%) | Flag & retain | Warranty KPIs must exclude flagged chronology; signal preserved for source-system investigation. |
| Duplicate stores (same name + city) | 6 pairs - 12 of 75 stores (16%) | Flag, no merge | Store-level reporting risks double counting; merging requires an authoritative identity source. |
| Ambiguous product name ("HomePod mini" x2) | 2 SKUs, conflicting category/price | Flag as ambiguous | Product-level reporting must key on product ID, never name. |
| Mixed-case column names | 9 columns across 2 sources | Fix (logged rename) | Conformity for joins and BI tooling. |

**Controls & assurance.** Row accounting is asserted in code: clean + quarantined = raw, per table. The quarantine path is contract-exercised and verified empty. 1.04M rows were loaded through PK/FK/CHECK enforcement with zero rejections. The audit tooling itself was cross-validated: a rows-vs-groups unit mismatch in the v1 scorecard was caught by three-way reconciliation and corrected - documented, including the lesson that a verdict can be internally consistent yet wrong. Final scorecard: every violation eliminated or flagged; unaccounted = 0 across all 13 checks.

**Key decisions.** Flag-not-delete for the 47.4% (preserving the fact table beats a clean-looking report); no entity merges without authoritative identity; raw schema stays constraint-free to preserve source truth; contract dtypes are human aliases resolved by the engine, so the specification never bends to implementation quirks.

**Limitations.** The source is a public synthetic dataset, widely used in tutorials - the contribution here is the governance pipeline, not novel data. Prices are static list prices (no price history), so revenue = quantity x current price. Warranty chronology (average ~800 days to claim) reflects generator artifacts; it is flagged and exposed rather than silently corrected. Multi-currency is not modeled despite 19 countries.

**Deliverables.** Damage report + findings ledger | rules contract v1.0.0 + cleaning log | reconciliation ledger ($0.00 variance) | MySQL raw/clean schemas + audit scorecard | star-schema BI views + ERD before/after | rerunnable Power Query workbook + recipe | this summary.