---
name: "review-panel"
description: "Multi-specialist panel review. Dispatches 6 parallel sub-agent reviewers (Architecture, Security & Supply Chain, UX/API, Codebase Consistency, QA Engineer, Devil's Advocate) then a Panel Arbiter synthesizes one verdict."
---

# Review Panel — Multi-Specialist Review Orchestration

The panel dispatches **6 specialist reviewers in parallel + 1 arbiter
= 7 persona sections in one verdict**. Each specialist runs as a
dedicated sub-agent so reviews execute concurrently. The Panel Arbiter
runs after all specialists complete, synthesizes findings, resolves
disagreements, and produces the final disposition.

## Agent Roster

| Agent | Lens | Dispatch |
|-------|------|----------|
| Architecture Reviewer | Structural patterns, cross-file impact, SOLID, module boundaries | Always, parallel |
| Security & Supply Chain Reviewer | Vulnerabilities, credential handling, dependency trust, supply chain integrity | Always, parallel |
| UX & API Reviewer | Public API ergonomics, error messages, naming, backwards compatibility | Always, parallel |
| Codebase Consistency Reviewer | Duplicate helpers, convention drift, style match with existing code | Always, parallel |
| QA Engineer | Test coverage gaps, missing edge-case tests, test quality, untested error paths | Always, parallel |
| Devil's Advocate | Assumes every line is wrong until proven otherwise; tries to break the code | Always, parallel |
| Panel Arbiter | Strategic synthesis, disagreement resolution, final disposition | Always, after all specialists |

## Routing Topology

```
  architecture  security  ux-api  consistency  qa-engineer  devils-advocate
       \__________|_________|__________|___________|__________/
                                  |
                                  v
                            panel-arbiter
                        (final call / arbiter)
```

- **Specialists raise findings independently** — no implicit consensus.
  Each runs as a separate sub-agent and cannot see the others' output.
- **Panel Arbiter synthesizes** after all specialist sub-agents complete.
  The arbiter receives every specialist's findings and resolves conflicts,
  weighs trade-offs, and makes the final call.

## Specialist Scope

### Architecture Reviewer

Reviews structural quality of the change:

- **Single Responsibility**: Does each new function/type/module have one clear job?
- **Cross-file impact**: Do changes ripple correctly through callers and dependents?
- **Abstraction level**: Are new abstractions justified or premature?
- **Module boundaries**: Are package/module imports clean? Any circular dependencies?
- **Error handling**: Are errors propagated correctly? No swallowed errors?
- **Pattern consistency**: Do new patterns match existing architectural conventions?

Anti-patterns to flag: god functions, shotgun surgery, feature envy,
inappropriate intimacy, premature abstraction.

### Security & Supply Chain Reviewer

Maps the change against vulnerability classes AND supply chain risk.
This reviewer operates with a **fails-closed** bias — when uncertain
whether a pattern is safe, flag it. False positives are preferable to
missed vulnerabilities.

**Important**: the fails-closed bias applies to **factual uncertainty
about whether code is safe**, not to value judgments about architectural
style. If you are unsure whether an input is validated, flag it. If you
merely prefer a different design, that belongs in the Architecture
Reviewer's scope.

**Vulnerability surfaces:**
- **Injection**: SQL, command, template, log, header injection
- **Authentication/authorization**: Token handling, permission checks, credential storage
- **Input validation**: Untrusted input at system boundaries
- **Secret management**: Hardcoded secrets, secrets in logs, config exposure
- **Cryptography**: Weak algorithms, improper random number generation

**Supply chain risk (critical focus):**
- **New dependencies**: Is the dependency necessary or can stdlib/existing deps cover it?
  Is it actively maintained? Does it have a known security track record? How many
  transitive dependencies does it pull in?
- **Dependency changes**: Version bumps, removed pins, loosened constraints. Do the
  changes match what's expected? Any yanked versions?
- **Lockfile integrity**: Does `go.sum`, `package-lock.json`, `yarn.lock`, `Cargo.lock`,
  etc. contain only expected changes? Unexpected hash changes are a red flag.
- **Build pipeline changes**: CI config, Makefile, Dockerfile, build scripts — do they
  introduce untrusted sources, download URLs, or execution of remote code?
- **Transitive trust**: Does the change increase the trust boundary? New external API
  calls, new download URLs, new certificate trust, new registry sources?
- **Vendored code**: If vendoring is used, do vendored changes match declared dependency
  changes? Unexplained vendored diffs are suspicious.

### UX & API Reviewer

Reviews the developer/user-facing surface:

- **Naming**: Are new functions, flags, types, and variables self-explanatory?
- **Error messages**: Does every error tell the user what went wrong and what to do next?
- **API ergonomics**: Are interfaces minimal and hard to misuse?
- **Backwards compatibility**: Does the change break existing callers?
- **Documentation**: Are new public APIs documented? Are existing docs updated?
- **Flag/option design**: Do new CLI flags or config options follow existing conventions?

### Codebase Consistency Reviewer

Ensures the PR does not introduce drift from existing codebase patterns.
This reviewer must **actively read existing code** in the repository —
grep and find to locate potential duplicates and existing conventions
rather than reviewing the diff in isolation.

- **Duplicate helpers**: Does the PR introduce a function, utility, or pattern that
  already exists elsewhere in the codebase? Search for similar implementations before
  accepting new ones. Grep for function names, key algorithmic patterns, and string
  constants that look reusable.
- **Convention adherence**: Does new code follow the same naming conventions, file
  organization, import ordering, and structural patterns as existing code in the
  same package/module?
- **Style match**: Does the code style (error handling idiom, logging pattern,
  test structure, comment style) match the surrounding codebase?
- **Shared utilities**: When the PR introduces logic that could be shared, does it
  use the project's established utility packages/modules rather than inlining?
- **Configuration patterns**: Do new config values, environment variables, or
  constants follow the existing naming and placement conventions?
- **Test patterns**: Do new tests follow the same structure, assertion style, and
  helper usage as existing tests in the same package?

### QA Engineer

Reviews test coverage and quality for the change:

- **Coverage gaps**: For each new or modified function with non-trivial logic,
  verify that tests exist. Flag public/exported functions that lack tests entirely.
- **Untested error paths**: Identify error branches, edge cases, and failure modes
  in the new code that have no corresponding test.
- **Test quality**: Are tests asserting meaningful behavior or just achieving line
  coverage? Look for tests that pass trivially, assert nothing, or test
  implementation details rather than behavior.
- **Edge cases**: Identify concrete edge-case inputs the author should test:
  empty inputs, nil/null, boundary values, concurrent access, large inputs,
  malformed data.
- **Regression coverage**: If the change fixes a bug, is there a test that would
  have caught the original bug and will prevent regression?
- **Concrete suggestions**: Do not just say "add tests." Suggest specific test
  scenarios with example inputs and expected outputs when possible.

### Devil's Advocate

The adversarial reviewer. Assumes **every line of code is wrong until
proven otherwise**. This reviewer's job is to try to break the code.

- **Logical correctness**: For each conditional, loop, and branch, construct
  an input or state that would cause it to fail. If you cannot construct one,
  say so explicitly — silence is not acquittal.
- **Hidden assumptions**: What does this code assume that is not enforced?
  Nil-safety, ordering guarantees, single-threaded access, input format,
  environment availability, file existence.
- **Off-by-one errors**: Examine loop bounds, slice operations, index arithmetic,
  range boundaries.
- **Race conditions**: If shared state is accessed, is it protected? If goroutines
  or threads are involved, can operations interleave unsafely?
- **Resource leaks**: Are file handles, connections, channels, locks, and
  goroutines properly cleaned up on all paths including error paths?
- **Failure modes**: What happens when the network is down? The file doesn't exist?
  The input is empty? The input is 10GB? The API returns 500? The context is
  cancelled? The disk is full?
- **Implicit coupling**: Does the code depend on ordering, timing, or side effects
  that are not guaranteed by the interface contract?
- **Prove it wrong or admit you can't**: For each finding, describe the specific
  scenario that breaks it. If you cannot find issues, state explicitly what you
  tested and why the code holds up.

## External Reviewers

The panel optionally includes external review tools that run alongside
the internal specialists. External reviewers execute as CLI commands
in parallel with the sub-agents, and their output is included in the
Panel Arbiter's synthesis input.

### Supported External Reviewers

| Name | CLI Tool | Invocation | Activation |
|------|----------|------------|------------|
| CodeRabbit | `coderabbit` | `coderabbit review --agent --base <base-ref>` | User passes `coderabbit` as argument; tool must be on PATH |

### How External Reviewers Integrate

- External reviewers are **not** sub-agents. They are CLI commands
  invoked via Bash, running in parallel with the sub-agent dispatch.
- Their stdout is captured as-is and included in the verdict under
  its own heading in the specialist findings section.
- The Panel Arbiter treats external reviewer output as a **peer
  specialist**. Its findings carry the same weight as internal
  specialists — corroboration strengthens confidence, conflicts
  require the same explicit resolution as any inter-specialist
  disagreement.
- If an external reviewer command fails (non-zero exit, tool not found),
  record the error in the verdict under that reviewer's heading and
  continue — never block the panel on an external tool failure.
- **Timeout**: external reviewer commands should be run with a
  reasonable timeout (5 minutes). If the command exceeds this, kill it
  and record a timeout error in the verdict.

## Execution Procedure

### Step 1 — Gather Context

The invoking command provides the diff, changed file list, base ref,
and any auto-loaded skill content. This is passed to all sub-agents.

**Large diffs** (over ~3000 lines): when the diff is very large,
instruct each sub-agent to focus on the highest-risk files in their
specialist area rather than attempting exhaustive line-by-line review.
Architecture and Security reviewers should prioritize new files and
public API changes; QA and Devil's Advocate should prioritize complex
logic and error-handling paths; Codebase Consistency should focus on
new helpers and patterns.

### Step 2 — Dispatch Parallel Specialist Sub-Agents & External Reviewers

If external reviewers were requested, launch their CLI commands via
Bash **in the same message** as the sub-agent dispatches so everything
runs concurrently. For example, if CodeRabbit was requested:

```bash
timeout 300 coderabbit review --agent --base <base-ref> 2>&1
```

Capture the full stdout/stderr as the external reviewer's findings.

Launch **all six specialist sub-agents in a single message** (one
Agent tool call per specialist) so they execute concurrently. Each
sub-agent receives:

- The full diff
- The list of changed files
- Any commit message / PR description context
- The specialist's scope description (from the relevant section above)
- Any auto-loaded language/profile skill content

Each sub-agent should be given `subagent_type: "general-purpose"`.
Do NOT set the `model` parameter — let sub-agents inherit the parent
model. Each sub-agent returns structured findings with file:line
references where possible.

**Sub-agent prompt template** (adapt scope per specialist):

```
You are the {Specialist Name} for a code review panel.

Your scope: {paste the specialist's scope section from above}

Changed Files: {file list}

Full Diff:
{diff}

Review the changes exclusively through your specialist lens. Produce
findings as a list, each with:
- Severity: BLOCKING | SUGGESTION | NOTE
- File:line reference (when applicable)
- Finding description
- Recommended action

Focus only on your specialist area. Do not review areas outside
your scope. Be specific and actionable. Reference file:line when
possible. If you find no issues in your area, say so explicitly
with a brief explanation of what you checked.
```

For the **Codebase Consistency Reviewer**, add to the prompt:

```
You have access to the full repository. Before accepting any new
helper function, utility, or pattern in the diff, actively search
the existing codebase for duplicates:

1. For each new function/method added, grep for similar function
   names and signatures in the repo.
2. For each new pattern (error handling, logging, config loading),
   check how the same thing is done elsewhere in the codebase.
3. Compare naming conventions, import ordering, and structural
   patterns against files in the same package/directory.
4. Check if the project has shared utility packages that should
   be used instead of inline implementations.

Report any duplicates or convention violations you find, with
pointers to the existing code that should be followed or reused.
```

For the **Devil's Advocate**, add to the prompt:

```
You must actively try to break every piece of new code. Do not
just read it — construct scenarios. For each function:

1. What input causes a panic/crash?
2. What state makes the conditional wrong?
3. What timing makes the concurrency unsafe?
4. What environment makes the assumption false?

If you cannot break it, say exactly what you tried and why
it held up. "No issues found" without evidence of effort is
not acceptable.
```

### Step 3 — Completeness Gate

After all sub-agents and external reviewers return, verify:

- Findings exist for all 6 internal specialists
- No sub-agent returned an error or an empty result (a result is
  "empty" if it contains no findings list and no explicit "no issues
  found" statement with explanation of what was checked)
- External reviewer output was captured (if requested). If an external
  reviewer failed or timed out, note the error but do not re-run —
  proceed with internal findings.

If any internal specialist produced an error or empty result,
re-dispatch that specialist's sub-agent **once**. If the retry also
fails, record the failure in the verdict under that specialist's
heading and proceed with the remaining findings. Do not retry more
than once per specialist.

### Step 4 — Panel Arbiter Synthesis

With all specialist findings (and any external reviewer output)
collected, perform Panel Arbiter synthesis directly (not as a
sub-agent — this runs in the main agent context to see the full
picture):

1. Read all specialist findings and external reviewer output
2. Identify any conflicts between specialists (e.g., Architecture
   says "extract this to a helper" but Codebase Consistency says
   "a similar helper already exists"; or Devil's Advocate flags a
   race condition but Architecture says the design is single-threaded)
3. Resolve conflicts with a clear rationale
4. Assign final disposition: APPROVE, REQUEST_CHANGES, or
   NEEDS_DISCUSSION
5. Compile required actions (blocking) vs optional follow-ups

**Disposition criteria:**

- **APPROVE**: No BLOCKING findings remain after synthesis, or all
  BLOCKING findings were resolved/refuted during arbitration.
- **REQUEST_CHANGES**: One or more BLOCKING findings remain that
  require code changes before merge.
- **NEEDS_DISCUSSION**: Findings raise questions that require author
  input to resolve — the arbiter cannot determine the correct fix
  without additional context (e.g., the intended behavior is ambiguous,
  a design trade-off requires product input, or a specialist flagged
  a pattern that may be intentional).

**Arbiter biases:**

- **Security over ergonomics** when they conflict
- **Codebase consistency over local elegance** when they conflict
- **Existing patterns over novel ones** unless the novel approach
  is demonstrably better
- **The Devil's Advocate's concerns** when they identify concrete
  failure scenarios — these are blocking unless another specialist
  provides a specific technical refutation (e.g., "this race cannot
  occur because the goroutine is only launched from a single-threaded
  init path, as shown at file:line")

**When all specialists report no issues**: this is a valid outcome
for clean, well-written changes. The arbiter should confirm the
APPROVE disposition with a brief summary of what was checked. Do not
manufacture findings to fill space.

### Step 5 — Emit Verdict

Load `verdict-template.md` (in the same directory as this skill file)
and fill it with the collected findings and arbitration. Present the
filled template to the user as the review output.

Rules:
- Produce exactly ONE verdict, not per-specialist outputs
- Keep all section headings from the template
- Include file:line references from specialist findings
- Panel Arbiter synthesis must address any inter-specialist conflicts
- Omit the "External Reviewers" section entirely when no external
  reviewers were requested — do not leave an empty section or
  a stray horizontal rule

## Quality Gates

A change passes when:

- [ ] Architecture Reviewer: structure and patterns are sound
- [ ] Security & Supply Chain Reviewer: no unmitigated vulnerability or supply chain risk
- [ ] UX & API Reviewer: public surfaces are clear and compatible
- [ ] Codebase Consistency Reviewer: no duplicate helpers, conventions match
- [ ] QA Engineer: adequate test coverage, edge cases addressed
- [ ] Devil's Advocate: no unrefuted failure scenarios
- [ ] Panel Arbiter: trade-offs ratified, disposition set
