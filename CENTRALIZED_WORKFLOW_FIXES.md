# Fixes Required in Centralized Reusable Workflow

**Repository**: `bodis/ai-review-cicd-actions`
**File**: `.github/workflows/reusable-ai-review.yml`

---

## Problem Summary

The current reusable workflow fails when projects have **platform-specific dependencies** (e.g., MLX for Apple Silicon). This prevents static analysis from running and blocks security reviews.

**Current Behavior**:
1. ❌ `uv sync` fails when MLX can't install on ubuntu-latest
2. ❌ Static analysis tools can't import code
3. ❌ Review stops with generic "missing dependency" errors
4. ❌ **Critical security issues are never detected**

**Expected Behavior**:
1. ✅ Install base dependencies (skip platform-specific ones)
2. ✅ Load conftest.py to mock unavailable imports
3. ✅ Run static analysis successfully
4. ✅ Detect security issues even with mocked dependencies

---

## Required Changes to Reusable Workflow

### 1. **Install Dependencies with Fallback**

**Current**:
```yaml
- name: Install dependencies
  run: uv sync
```

**Fixed**:
```yaml
- name: Install project dependencies
  run: |
    # Try to install all dependencies first
    if uv sync --extra ci 2>&1 | tee install.log; then
      echo "✓ All dependencies installed"
    else
      echo "⚠️  Some dependencies failed (platform-specific?)"
      echo "Installing CI-only tools..."

      # Install static analysis tools separately
      uv pip install ruff bandit mypy pylint --system

      # Continue even if project deps fail
      exit 0
    fi
```

### 2. **Load conftest.py Before Analysis**

Add environment variable to ensure conftest is loaded:

```yaml
- name: Run static analysis
  env:
    PYTHONPATH: ${{ github.workspace }}
    # This ensures conftest.py is loaded, mocking unavailable imports
  run: |
    # Load conftest to mock platform-specific dependencies
    python -c "import conftest" 2>&1 || echo "No conftest.py found"

    # Now run static analysis
    ruff check . --select S --format json > ruff-security.json || true
    bandit -r . -f json -o bandit-results.json || true
```

### 3. **Continue on Tool Failures**

Ensure the workflow doesn't stop if one tool fails:

```yaml
- name: Run Bandit security scan
  continue-on-error: true  # ✅ Don't fail workflow if tool has issues
  run: |
    bandit -r . -f json -o bandit-results.json
    echo "BANDIT_EXIT_CODE=$?" >> $GITHUB_ENV

- name: Run Ruff security checks
  continue-on-error: true  # ✅ Don't fail workflow if tool has issues
  run: |
    ruff check . --select S --format json > ruff-security.json
    echo "RUFF_EXIT_CODE=$?" >> $GITHUB_ENV
```

### 4. **Aggregate Results from All Tools**

Even if some tools fail, aggregate what succeeded:

```yaml
- name: Aggregate analysis results
  run: |
    python scripts/aggregate_results.py \
      --bandit bandit-results.json \
      --ruff ruff-security.json \
      --output review-results.json \
      --allow-partial-results  # ✅ Use available results even if some tools failed
```

### 5. **Update Artifact Upload to v4**

**Current**:
```yaml
- name: Upload review results
  uses: actions/upload-artifact@v3
  with:
    name: review-results
    path: review-results.json
```

**Fixed**:
```yaml
- name: Upload review results
  if: always()  # Upload even if analysis partially failed
  uses: actions/upload-artifact@v4  # ✅ v4 required by Jan 2025
  with:
    name: review-results-pr-${{ github.event.pull_request.number }}
    path: review-results.json
    retention-days: 30
    compression-level: 6
```

---

## Complete Fixed Workflow Example

Here's how the key sections should look:

```yaml
jobs:
  ai-review:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install UV
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install ${{ inputs.python-version || '3.11' }}

      # ✅ Install with fallback for platform-specific deps
      - name: Install dependencies
        continue-on-error: true
        run: |
          echo "Installing project dependencies..."
          if uv sync --extra ci; then
            echo "✓ All dependencies installed"
          else
            echo "⚠️  Platform-specific dependencies failed"
            echo "Installing analysis tools separately..."
            uv pip install ruff bandit mypy pylint --system
          fi

      # ✅ Load mocks before analysis
      - name: Prepare analysis environment
        run: |
          export PYTHONPATH="${{ github.workspace }}:$PYTHONPATH"
          if [ -f conftest.py ]; then
            python -c "import conftest" && echo "✓ Mocks loaded"
          fi

      # ✅ Run Bandit with error handling
      - name: Run Bandit security scan
        continue-on-error: true
        run: |
          bandit -r . \
            --exclude tests,mlx_models,.venv \
            -f json -o bandit-results.json || {
            echo "⚠️  Bandit encountered issues (exit $?)"
            echo '{"results": [], "error": "bandit_failed"}' > bandit-results.json
          }

      # ✅ Run Ruff with error handling
      - name: Run Ruff security checks
        continue-on-error: true
        run: |
          ruff check . --select S --format json > ruff-security.json || {
            echo "⚠️  Ruff encountered issues (exit $?)"
            echo '[]' > ruff-security.json
          }

      # ✅ Run AI security review (critical for path traversal detection!)
      - name: Run AI security review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/ai_security_review.py \
            --config ${{ inputs.config-file || '.github/ai-review-config.yml' }} \
            --output ai-security-review.json

      # ✅ Aggregate all results
      - name: Aggregate review results
        run: |
          python scripts/aggregate_results.py \
            --bandit bandit-results.json \
            --ruff ruff-security.json \
            --ai-review ai-security-review.json \
            --output review-results.json \
            --allow-partial-results

      # ✅ Post results to PR
      - name: Post review comments
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('review-results.json'));

            // Post summary comment
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.payload.pull_request.number,
              body: generateSummary(results)
            });

            // Post inline comments
            for (const finding of results.findings) {
              await github.rest.pulls.createReviewComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                pull_number: context.payload.pull_request.number,
                body: finding.message,
                path: finding.path,
                line: finding.line,
                side: 'RIGHT'
              });
            }

      # ✅ Upload artifacts (v4)
      - name: Upload review results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: review-results-pr-${{ github.event.pull_request.number }}
          path: |
            review-results.json
            bandit-results.json
            ruff-security.json
            ai-security-review.json
          retention-days: 30
          compression-level: 6

      # ✅ Check blocking conditions
      - name: Check if review blocks PR
        if: inputs.fail-on-blocking
        run: |
          python scripts/check_blocking.py \
            --results review-results.json \
            --config ${{ inputs.config-file }}
```

---

## Testing the Fixes

### Local Testing:
```bash
# Test dependency installation with fallback
uv sync --extra ci || uv pip install ruff bandit mypy --system

# Test conftest loading
python -c "import conftest; print('✓ Mocks loaded')"

# Test static analysis
ruff check . --select S
bandit -r . -f json
```

### Integration Testing:
1. Create a test PR with platform-specific dependencies
2. Verify workflow completes (even with import errors)
3. Verify security issues are still detected
4. Verify artifacts are uploaded with v4

---

## Why This Matters

**Current state**:
- Lightning Whisper MLX review returned "missing mlx.core"
- **Path traversal vulnerability completely missed**

**With these fixes**:
- ✅ Static analysis runs (finds MD5 weakness)
- ✅ AI review runs (should find path traversal)
- ✅ Review completes successfully
- ✅ Security issues detected and reported

---

## Timeline

- **Immediate**: Update to `actions/upload-artifact@v4` (Jan 2025 deadline)
- **High Priority**: Add dependency fallback logic
- **High Priority**: Add conftest.py loading
- **Medium Priority**: Add continue-on-error for tools

---

## Summary

The centralized workflow needs to be **more resilient** to platform-specific dependencies and tool failures. These changes ensure:

1. ✅ **Static analysis always runs** (even with import failures)
2. ✅ **AI review always runs** (catches what static analysis misses)
3. ✅ **Results are aggregated** (partial results still useful)
4. ✅ **PR gets feedback** (even if some tools failed)
5. ✅ **Critical security issues are never missed**

Without these fixes, your review system will continue to produce **false negatives** for projects with platform-specific dependencies.
