---
description: Update Prow vendoring across all OpenShift CI repositories
argument-hint: "[prow-commit-sha]"
---

## Name
ci:update-prow

## Synopsis
```
/ci:update-prow [prow-commit-sha]
```

## Description

The `update-prow` command automates updating the Prow dependency across all OpenShift CI repositories that vendor it. This is a multi-repository update that requires coordinated PRs.

**Repositories updated:**
1. `openshift/ci-tools` - Primary CI tooling repository
2. `openshift/ci-chat-bot` - Slack bot for CI interactions
3. `openshift/release-controller` - Release controller for OpenShift

The command handles:
- Cloning each repository to a working directory
- Updating the `sigs.k8s.io/prow` dependency
- Running `go mod tidy` and `go mod vendor`
- Running tests and fixing any breaking changes
- Creating feature branches and commits
- Pushing branches and creating draft PRs
- Cross-linking all PRs in their descriptions

## Implementation

### Phase 1: Setup and Preparation

1. **Create working directory:**
   ```bash
   mkdir -p .work/update-prow
   cd .work/update-prow
   ```

2. **Determine target Prow version:**
   - If `prow-commit-sha` argument is provided, use that
   - Otherwise, fetch the latest commit from `kubernetes-sigs/prow` main branch:
     ```bash
     gh api repos/kubernetes-sigs/prow/commits/main --jq '.sha'
     ```

3. **Clone all repositories** (can be done in parallel):
   ```bash
   gh repo clone openshift/ci-tools
   gh repo clone openshift/ci-chat-bot
   gh repo clone openshift/release-controller
   ```

### Phase 2: Update Each Repository

For each repository, perform the following steps:

1. **Create feature branch:**
   ```bash
   cd <repo-name>
   git checkout -b update-prow-$(date +%Y%m%d)
   ```

2. **Update Prow dependency:**
   ```bash
   go get sigs.k8s.io/prow@<target-sha>
   go mod tidy
   go mod vendor
   ```

3. **Run tests to identify breaking changes:**
   ```bash
   make test
   # or
   go test ./...
   ```

4. **Fix any breaking changes:**
   - Analyze test failures
   - Update code to accommodate API changes
   - Re-run tests until passing
   - Common issues include:
     - Changed function signatures in Prow libraries
     - New required fields in structs
     - Deprecated APIs that have been removed

5. **Verify the build:**
   ```bash
   make build
   # or
   go build ./...
   ```

6. **Stage and commit changes:**
   ```bash
   git add -A
   git commit -m "vendor: bump prow dependency"
   ```

7. **Push branch:**
   ```bash
   git push -u origin update-prow-$(date +%Y%m%d)
   ```

### Phase 3: Create Pull Requests

1. **Create PR for ci-tools first** (as the primary repository):
   ```bash
   cd ci-tools
   gh pr create --title "vendor: bump prow dependency" --body "$(cat <<'EOF'
   Updates the prow vendoring to the latest version.

   Related PRs:
   - ci-chat-bot: (pending)
   - release-controller: (pending)
   EOF
   )" --draft
   ```

2. **Create PRs for ci-chat-bot and release-controller:**
   ```bash
   cd ci-chat-bot
   gh pr create --title "vendor: bump prow dependency" --body "$(cat <<'EOF'
   Updates the prow vendoring to the latest version.

   Related PRs:
   - ci-tools: <ci-tools-pr-url>
   - release-controller: (pending)
   EOF
   )" --draft
   ```

   ```bash
   cd release-controller
   gh pr create --title "vendor: bump prow dependency" --body "$(cat <<'EOF'
   Updates the prow vendoring to the latest version.

   Related PRs:
   - ci-tools: <ci-tools-pr-url>
   - ci-chat-bot: <ci-chat-bot-pr-url>
   EOF
   )" --draft
   ```

### Phase 4: Update PR Descriptions with Cross-Links

1. **Update ci-tools PR** with links to the other PRs:
   ```bash
   gh pr edit <ci-tools-pr-number> --body "$(cat <<'EOF'
   Updates the prow vendoring to the latest version.

   Related PRs:
   - ci-chat-bot: <ci-chat-bot-pr-url>
   - release-controller: <release-controller-pr-url>
   EOF
   )"
   ```

2. **Update ci-chat-bot PR** with the release-controller link:
   ```bash
   gh pr edit <ci-chat-bot-pr-number> --body "$(cat <<'EOF'
   Updates the prow vendoring to the latest version.

   Related PRs:
   - ci-tools: <ci-tools-pr-url>
   - release-controller: <release-controller-pr-url>
   EOF
   )"
   ```

### Phase 5: Summary and Next Steps

1. **Display all PR URLs to the user:**
   ```
   Prow update PRs created:

   1. ci-tools: https://github.com/openshift/ci-tools/pull/XXXX
   2. ci-chat-bot: https://github.com/openshift/ci-chat-bot/pull/XXXX
   3. release-controller: https://github.com/openshift/release-controller/pull/XXXX

   All PRs are cross-linked and created as drafts.
   ```

2. **Provide guidance on next steps:**
   - Review CI results on each PR
   - Address any additional test failures
   - Mark PRs as ready for review once CI passes
   - Coordinate merge order (typically ci-tools first)

## Return Value

- **Success**: URLs of all three created PRs
- **Partial Success**: URLs of successfully created PRs with error details for failures
- **Error**: Description of failure (e.g., clone failed, build failed, PR creation failed)

## Error Handling

1. **Clone failures**: Check network connectivity and GitHub authentication
2. **Build failures**: May indicate incompatible Go version or missing dependencies
3. **Test failures**: Analyze and fix breaking changes (this is expected and normal)
4. **PR creation failures**: Verify GitHub CLI authentication and repository permissions

## Examples

1. **Update to latest Prow version:**
   ```
   /ci:update-prow
   ```

2. **Update to a specific Prow commit:**
   ```
   /ci:update-prow abc123def456789
   ```

## Notes

- **Working directory**: All work is done in `.work/update-prow/`
- **Branch naming**: Branches are named `update-prow-YYYYMMDD`
- **Draft PRs**: All PRs are created as drafts to allow review before marking ready
- **Merge order**: Generally merge ci-tools first, then ci-chat-bot and release-controller
- **CI time**: Each repository's CI may vary; ci-tools typically has the most comprehensive tests
- **Breaking changes**: Prow updates often include API changes that require code fixes

## Arguments
- **$1** (prow-commit-sha): Optional. Specific Prow commit SHA to update to. If not provided, uses the latest commit from kubernetes-sigs/prow main branch.
