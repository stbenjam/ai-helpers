---
description: "Multi-specialist panel review with 6 parallel sub-agents, optional external reviewers, and CEO arbitration"
argument-hint: "[pr-url-or-number] [external-reviewer...]"
---

## Name
code-review:panel-review

## Synopsis
```
/code-review:panel-review [pr-url-or-number] [external-reviewer...]
```

## Description
The `panel-review` command runs a multi-specialist review panel. Six specialist reviewers execute in parallel as sub-agents, each examining the changes through a different lens. Optionally, external review tools (like CodeRabbit) run alongside them. After all reviewers complete, a CEO arbiter synthesizes findings, resolves disagreements, and produces a single verdict.

The internal panel:

1. **Architecture Reviewer** -- structural patterns, SOLID principles, cross-file impact
2. **Security & Supply Chain Reviewer** -- vulnerabilities, dependency trust, supply chain integrity
3. **UX & API Reviewer** -- naming, error messages, API ergonomics, backwards compatibility
4. **Codebase Consistency Reviewer** -- duplicate helpers, convention drift, style match
5. **QA Engineer** -- test coverage gaps, missing edge-case tests, concrete test suggestions
6. **Devil's Advocate** -- assumes every line is wrong, tries to break the code

Optional external reviewers (passed as arguments):

- **coderabbit** -- runs `coderabbit review --agent --base <base-ref>`

After all reviewers complete, the **CEO Arbiter** synthesizes and arbitrates.

No arguments are required. By default, the command diffs the current branch against its upstream merge base. Language and profile skills are auto-detected.

## Implementation

### Step 0 -- Determine Diff Target & External Reviewers

Parse `$ARGUMENTS`. Arguments are positional and unordered. Classify each:

- A **PR URL** (contains `github.com` and `/pull/`) -> use `gh pr diff` and `gh pr view` to fetch the diff and metadata.
- A **PR number** (bare integer) -> use it with the current repo's remote.
- A **known external reviewer name** (e.g., `coderabbit`) -> add to the external reviewer list.

#### Determine base ref

Whether or not a PR identifier was provided, resolve the base ref so the
diff always matches what the PR actually targets:

1. **Check for an open PR on the current branch:**
   ```bash
   gh pr view --json baseRefName --jq '.baseRefName' 2>/dev/null
   ```
   If this succeeds, the current branch has an open PR. Use the returned
   base branch name (e.g., `main`). Determine which remote tracks it:
   check `upstream` first, then `origin`.

2. **If no open PR exists, detect the upstream default branch:**
   ```bash
   gh repo view --json parent --jq '.parent.defaultBranchRef.name' 2>/dev/null
   ```
   If this returns a value, the repo is a fork -- use the parent's default
   branch with the `upstream` remote.

3. **If not a fork (no parent), use origin's default branch:**
   ```bash
   gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null
   ```
   Use this with the `origin` remote.

4. **Fetch the resolved remote/branch before diffing:**
   ```bash
   git fetch <remote> <branch>
   ```

5. **Generate the diff** using three-dot notation against the resolved ref:
   ```bash
   git diff <remote>/<branch>...HEAD
   git diff --name-only <remote>/<branch>...HEAD
   git log --format='%s%n%b' <remote>/<branch>...HEAD
   ```

6. If a **PR identifier was provided** in the arguments, also fetch the PR
   metadata (title, body, author) via `gh pr view` for richer context. The
   diff still comes from the base ref resolution above.

If the diff is empty (no changes), inform the user and exit.

### Step 1 -- Auto-detect Language & Load Skills

- Auto-detect the primary language from changed file extensions:
  - `.go` -> `go`
  - `.py` -> `python`
  - `.rs` -> `rust`
  - `.ts`, `.tsx` -> `typescript`
  - `.java` -> `java`
- Check for a matching language skill at `skills/lang-<lang>/SKILL.md` relative to the plugin root. If it exists, read and store its content.
- Auto-discover profile skills: check if any `skills/profile-*/SKILL.md` exists. For each, read the profile's description/scope and determine if it matches the current repository (by repo name, directory structure, or other heuristics). Load matching profiles.
- These are passed to sub-agents as supplementary context -- no flags needed.

### Step 2 -- Read the Review Panel Skill

Read `skills/review-panel/SKILL.md` relative to the plugin root directory. This defines the specialist scopes, routing topology, and execution procedure. Follow its instructions for the remaining steps.

### Step 3 -- Dispatch Parallel Specialist Sub-Agents & External Reviewers

Launch **all six specialist sub-agents AND any external reviewer commands in a single message** so everything runs concurrently.

**Internal sub-agents:** Each receives:
- The full diff
- The list of changed files
- Commit messages or PR description (for context)
- The specialist's scope (from the skill file)
- Auto-loaded language/profile skill content (if any)

Use `subagent_type: "general-purpose"` for each. Do NOT set the `model` parameter.

Each sub-agent prompt should follow the template in the skill file. Include the additional codebase-search instructions for the Codebase Consistency Reviewer and the adversarial instructions for the Devil's Advocate.

Each sub-agent returns findings as a list with:
- **Severity**: BLOCKING, SUGGESTION, or NOTE
- **File:line** reference (when applicable)
- **Finding** description
- **Recommended action**

**External reviewers:** For each requested external reviewer, launch a Bash command in the same message:

| Reviewer | Command |
|----------|---------|
| `coderabbit` | `coderabbit review --agent --base <base-ref> 2>&1` |

Where `<base-ref>` is the same base branch/ref determined in Step 0 (e.g., `upstream/main`). Capture full stdout/stderr. If the command fails or the tool is not found, record the error and continue.

### Step 4 -- Completeness Gate

After all sub-agents and external reviewers return, verify findings exist for all 6 internal specialists. If any sub-agent failed or returned empty, re-dispatch it. External reviewer failures are noted but do not block.

### Step 5 -- CEO Arbitration

Perform CEO arbitration directly in the main agent context (not as a sub-agent). The skill file defines the CEO's biases and procedure:

1. Read all specialist findings
2. Identify conflicts between specialists
3. Resolve conflicts with clear rationale
4. Set disposition: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
5. Compile required actions vs optional follow-ups

### Step 6 -- Emit Verdict

Read `skills/review-panel/assets/verdict-template.md` and fill it with findings and arbitration. Present the completed verdict to the user.

### Critical Rules

- **All six specialists AND external reviewers run in parallel** -- launch them in one message, not sequentially.
- **Exactly one verdict** -- never emit per-specialist outputs or progress comments.
- **CEO runs last** -- only after all specialist and external reviewer findings are collected.
- **Be specific** -- every finding must include file:line when possible.
- **Be actionable** -- every finding must include a recommended fix.
- **Do not review unchanged code** -- focus exclusively on the diff.
- **Codebase Consistency must search** -- it must actively grep/find existing code, not just review the diff.
- **Devil's Advocate must try to break things** -- "no issues" without evidence of effort is not acceptable.
- **External reviewer failures are non-blocking** -- note the error, continue with internal findings.

## Return Value
- **Format**: Structured verdict using the template from `skills/review-panel/assets/verdict-template.md`.
- **Success**: Verdict with APPROVE or NEEDS_DISCUSSION disposition.
- **Failure**: Verdict with REQUEST_CHANGES and blocking findings listed.

## Examples

1. **Review current branch (default)**:
   ```
   /code-review:panel-review
   ```
   Diffs current branch against upstream/main (or best available base), auto-detects language, runs all six specialists in parallel.

2. **Review with CodeRabbit**:
   ```
   /code-review:panel-review coderabbit
   ```
   Runs the full internal panel plus CodeRabbit CLI review in parallel.

3. **Review a specific PR with CodeRabbit**:
   ```
   /code-review:panel-review https://github.com/openshift/hypershift/pull/789 coderabbit
   ```
   Fetches the PR diff, runs internal panel + CodeRabbit, CEO arbitrates all findings.

4. **Review by PR number in current repo**:
   ```
   /code-review:panel-review 456
   ```

## Arguments
- PR identifier (optional): Full GitHub PR URL or PR number. If omitted, diffs current branch against its upstream merge base.
- External reviewers (optional, repeatable): Names of external review tools to include. Currently supported: `coderabbit`. Each runs in parallel with internal specialists.
