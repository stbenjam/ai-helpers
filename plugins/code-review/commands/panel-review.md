---
description: "Comprehensive multi-perspective code review with architecture, security, consistency, QA, and adversarial analysis"
argument-hint: "[pr-url-or-number] [coderabbit]"
---

## Name
code-review:panel-review

## Synopsis
```
/code-review:panel-review [pr-url-or-number] [external-reviewer...]
```

## Description
The `panel-review` command runs a multi-specialist review panel. Six specialist reviewers execute in parallel as sub-agents, each examining the changes through a different lens. Optionally, external review tools (like CodeRabbit) run alongside them. After all reviewers complete, an arbiter synthesizes findings, resolves disagreements, and produces a single verdict.

The internal panel:

1. **Architecture Reviewer** — structural patterns, SOLID principles, cross-file impact
2. **Security & Supply Chain Reviewer** — vulnerabilities, dependency trust, supply chain integrity
3. **UX & API Reviewer** — naming, error messages, API ergonomics, backwards compatibility
4. **Codebase Consistency Reviewer** — duplicate helpers, convention drift, style match
5. **QA Engineer** — test coverage gaps, missing edge-case tests, concrete test suggestions
6. **Devil's Advocate** — assumes every line is wrong, tries to break the code

Optional external reviewers (passed as arguments):

- **coderabbit** — runs `coderabbit review --agent --base <base-ref>`

After all reviewers complete, the **Panel Arbiter** synthesizes and arbitrates.

This command does not perform build verification. Use `/code-review:pr` if build verification is needed.

No arguments are required. By default, the command diffs the current branch against its upstream merge base. Language and profile skills are auto-detected.

## Implementation

### Step 0 — Determine Diff Target & External Reviewers

Split `$ARGUMENTS` on whitespace (ignore empty tokens). Classify each argument by content:

- A **PR URL** (contains `github.com` and `/pull/`) → use `gh pr diff` and `gh pr view` to fetch the diff and metadata.
- A **PR number** (bare integer) → use it with the current repo's remote.
- A **known external reviewer name** → add to the external reviewer list. Currently supported: `coderabbit`.
- **Anything else** → emit a warning: "Unrecognized argument: '{arg}'. Known external reviewers: coderabbit. PR identifiers must be a bare integer or a GitHub URL containing /pull/." Ignore the argument and continue.

If more than one PR identifier is detected, emit an error: "Multiple PR identifiers provided. Please provide at most one." and exit.

#### Pre-check: verify HEAD is on a branch

Run `git symbolic-ref --short HEAD 2>/dev/null`. If this fails, HEAD is detached. Warn the user that panel-review works best on a named branch. If a PR URL or number was provided, proceed using `gh pr diff` for the diff instead of local three-dot diff. Otherwise, exit with a suggestion to check out a branch.

#### Determine base ref

Whether or not a PR identifier was provided, resolve the base ref so the diff always matches what the PR actually targets:

1. **Check for an open PR on the current branch:**
   ```bash
   gh pr view --json baseRefName --jq '.baseRefName' 2>/dev/null
   ```
   If this exits 0 **and produces non-empty output**, the current branch has an open PR. Use the returned base branch name (e.g., `main`). Determine which remote has that branch by running `git ls-remote --heads <remote> <branch>` for `upstream` first, then `origin`. Use the first remote that has the branch.

2. **If no open PR exists (or step 1 returned empty), detect the upstream default branch:**
   ```bash
   gh repo view --json parent --jq '.parent.defaultBranchRef.name' 2>/dev/null
   ```
   If this returns a non-empty value, the repo is a fork — use the parent's default branch with the `upstream` remote.

3. **If not a fork (no parent), use origin's default branch:**
   ```bash
   gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null
   ```
   Use this with the `origin` remote.

4. **Terminal fallback:** If none of the above steps produce a base ref (e.g., `gh` is not installed, not authenticated, or the repo has no GitHub remote), inform the user: "Could not determine base branch. Ensure `gh` CLI is installed and authenticated (`gh auth status`), and that this repository has a GitHub remote configured." Exit.

5. **Fetch the resolved remote/branch before diffing:**
   ```bash
   git fetch <remote> <branch>
   ```
   If `git fetch` fails, warn the user with the error and exit. Do not proceed with a potentially stale local ref.

6. **Generate the diff** using three-dot notation against the resolved ref:
   ```bash
   git diff "<remote>/<branch>...HEAD"
   git diff --name-only "<remote>/<branch>...HEAD"
   git log --format='%s%n%b' "<remote>/<branch>...HEAD"
   ```
   If the three-dot diff fails (e.g., no merge base in an orphan branch or shallow clone), inform the user and exit.

7. If a **PR identifier was provided** in the arguments, also fetch the PR metadata (title, body, author) via `gh pr view` for richer context.

If the diff is empty (no changes), inform the user and exit.

### Step 1 — Auto-detect Language & Load Skills

- Auto-detect the primary language from changed file extensions:
  - `.go` → `go`
  - `.py` → `python`
  - `.rs` → `rust`
  - `.ts`, `.tsx` → `typescript`
  - `.java` → `java`
  - If changed files span multiple languages, load skills for the most prevalent language by file count. If no language matches the supported list, proceed without a language skill.
- Check for a matching language skill at `skills/lang-<lang>/SKILL.md` relative to the plugin root. If it exists, read and store its content.
- Auto-discover profile skills: check if any `skills/profile-*/SKILL.md` exists. For each, read the profile's description/scope and determine if it matches the current repository (by repo name, directory structure, or other heuristics). Load matching profiles.
- These are passed to sub-agents as supplementary context — no flags needed.

### Step 2 — Execute the Review Panel

Read `skills/review-panel/SKILL.md` relative to the plugin root directory. This defines the specialist scopes, routing topology, and full execution procedure. **Follow its instructions for all remaining steps** — dispatch sub-agents, run the completeness gate, perform arbitration, and emit the verdict.

Pass to the skill:
- The full diff, changed file list, and base ref from Step 0
- Commit messages or PR metadata for context
- Auto-loaded language/profile skill content from Step 1
- The list of requested external reviewers (if any)

### Critical Rules

- **All six specialists AND external reviewers run in parallel** — launch them in one message, not sequentially.
- **Exactly one verdict** — never emit per-specialist outputs or progress comments.
- **Arbiter runs last** — only after all specialist and external reviewer findings are collected.
- **Be specific** — every finding must include file:line when possible.
- **Be actionable** — every finding must include a recommended fix.
- **Do not review unchanged code** — focus exclusively on the diff.
- **Codebase Consistency must search** — it must actively grep/find existing code, not just review the diff.
- **Devil's Advocate must try to break things** — "no issues" without evidence of effort is not acceptable.
- **External reviewer failures are non-blocking** — note the error, continue with internal findings.

## Return Value
- **Format**: Structured verdict using the template from `skills/review-panel/verdict-template.md`.
- **Success**: Verdict with APPROVE or NEEDS_DISCUSSION disposition.
- **Failure**: Verdict with REQUEST_CHANGES and blocking findings listed.

## Examples

1. **Review current branch (default)**:
   ```
   /code-review:panel-review
   ```
   Diffs current branch against the upstream base, auto-detects language, runs all six specialists in parallel.

2. **Review with CodeRabbit**:
   ```
   /code-review:panel-review coderabbit
   ```
   Runs the full internal panel plus CodeRabbit CLI review in parallel.

3. **Review a specific PR with CodeRabbit**:
   ```
   /code-review:panel-review https://github.com/openshift/hypershift/pull/789 coderabbit
   ```
   Fetches the PR diff, runs internal panel + CodeRabbit, arbiter synthesizes all findings.

4. **Review by PR number in current repo**:
   ```
   /code-review:panel-review 456
   ```

## See Also
- `/code-review:pr` — single-reviewer analysis with build verification, language-specific idiom checks, and SOLID/DRY compliance
- `/code-review:pre-commit-review` — lightweight pre-commit review of staged changes

## Arguments:
- PR identifier (optional): Full GitHub PR URL or PR number. If omitted, diffs current branch against its upstream merge base.
- External reviewers (optional, repeatable): Names of external review tools to include. Currently supported: `coderabbit`. Each runs in parallel with internal specialists.
