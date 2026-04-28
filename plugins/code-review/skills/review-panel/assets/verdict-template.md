<!--
Verdict template for the Review Panel skill.

Load this ONLY at synthesis time, after all specialists have produced
findings and CEO arbitration is complete.

Rules:
- Keep all section headings exactly as written.
- Adapt the body of each section to the changes under review.
- Do NOT split this across multiple outputs.
- Include file:line references from specialist findings.
- CEO arbitration must address any inter-specialist conflicts.
- The "External Reviewers" section is only included when external
  reviewers were requested. If none were requested, omit it entirely.
-->

## Review Panel Verdict

**Disposition**: <APPROVE | REQUEST_CHANGES | NEEDS_DISCUSSION> <optional one-line qualifier>

---

### Specialist Findings

**Architecture Reviewer**: <findings on structural patterns, SOLID, cross-file impact, module boundaries>

**Security & Supply Chain Reviewer**: <findings on vulnerability surfaces, credential handling, dependency trust, supply chain integrity, lockfile changes, build pipeline risk>

**UX & API Reviewer**: <findings on naming, error messages, API ergonomics, backwards compatibility>

**Codebase Consistency Reviewer**: <findings on duplicate helpers, convention adherence, style match, shared utility usage>

**QA Engineer**: <findings on test coverage gaps, untested error paths, missing edge-case tests, concrete test suggestions>

**Devil's Advocate**: <findings on broken assumptions, failure scenarios, race conditions, resource leaks, off-by-one errors. If no issues found, state what was tried and why the code holds up.>

---

### External Reviewers
<!-- Include this section ONLY when external reviewers were requested. Omit entirely otherwise. -->

**CodeRabbit**: <full output from `coderabbit review --agent`, or error message if the tool failed>

---

### CEO Arbitration

<Synthesize all findings -- internal specialists and external reviewers (if any). Resolve any disagreements between reviewers. Where an external reviewer corroborates an internal specialist, note the convergence. Where they conflict, explain the resolution. If Devil's Advocate flags a concrete failure scenario, it is blocking unless another reviewer can definitively refute it. Ratify the disposition. State the strategic call. If reviewers agreed and the change is straightforward, say so plainly in one or two sentences.>

---

### Required Actions Before Merge

1. <required action with file:line pointer. If disposition is APPROVE with no required actions, write "None." -- do not omit the section.>

---

### Optional Follow-ups

- <follow-up suggestion out of scope for this change but worth tracking>
