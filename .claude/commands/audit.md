# Smart Contract Security Audit

**Purpose**: Run comprehensive security audit on Solidity contracts using automated tools (Slither, Mythril) with beginner-friendly analysis.

**Usage**: `/audit [contract-path]` or `/audit` (auto-detect)

---

## Phase 0: Prerequisites Check

You MUST perform these checks before proceeding with the audit:

### 1. Load Configuration

Read `.audit/config.json` to get:
- Tool paths and timeouts
- Contract size limits
- False positive patterns
- INoT analysis configuration
- Security score weights

### 2. Determine Contract Path

If user provided path: Use it
If not provided:
- Check for `contracts/src/` directory
- List `.sol` files
- If only one contract: Use it
- If multiple: Ask user to specify

### 3. Validate Contract

**Check file exists**:
```bash
test -f [contract-path] || echo "ERROR: Contract not found"
```

**Count lines of code**:
```bash
wc -l [contract-path]
```
- If > 1500 lines: ERROR - Contract exceeds size limit. Recommend splitting or professional audit.

**Extract contract name** from filename (e.g., `GliskNFT.sol` → `glisknft`)

### 4. Check Prerequisites

**Foundry installed**:
```bash
forge --version
```
- If missing: ERROR - Install with `curl -L https://foundry.paradigm.xyz | bash && foundryup`

**Contract compiles**:
```bash
cd contracts && forge build
```
- If fails: ERROR - Show compilation errors and suggest fixes (check imports, run `forge install`)

**Tests exist and pass** (optional, warn if fail):
```bash
cd contracts && forge test
```
- If tests fail: WARN - Tests failing, audit will continue but note in report

**Test coverage** (optional):
```bash
cd contracts && forge coverage 2>&1 | grep -E "Overall|Total"
```
- Extract coverage percentage for report

**Slither available**:
```bash
uvx --from slither-analyzer slither --version || slither --version
```
- If missing: ERROR - Install with `pip3 install slither-analyzer` or use `uvx`

**Mythril available** (optional):
```bash
myth version
```
- If missing: WARN - Mythril not available, audit will run with Slither only

### 5. Prerequisites Summary

Display checklist:
```markdown
## Prerequisites Check

- [X] Foundry installed: forge 0.2.0
- [X] Contract compiles: build successful
- [X] Tests: [PASS/FAIL/NOT RUN]
- [X] Test coverage: [XX]% line coverage
- [X] Slither available: [version]
- [X] Mythril available: [version or NOT AVAILABLE]

**Contract Info**:
- Path: [contract-path]
- Size: [XXX] lines
- Within limits: ✅ (max 1500 lines)

**Proceeding with comprehensive audit...**
```

---

## Phase 1: Security Scanning

Generate timestamp: `AUDIT_ID={contract-name}-$(date +%Y-%m-%dT%H-%M-%S)`

Create output directories:
```bash
mkdir -p .audit/raw
mkdir -p .audit/history/{contract-name}
mkdir -p .audit/reports/{contract-name}
mkdir -p .audit/findings
```

### 1. Run Slither

```bash
cd contracts
uvx --from slither-analyzer slither [contract-path] --json ../.audit/raw/${AUDIT_ID}-slither.json --timeout 30
```

**Track execution**:
- Start time
- Monitor for timeout (30s from config)
- Capture exit code
- Parse JSON output

**Handle errors**:
- Exit code 0: Success
- Exit code 255: Timeout
- Other: Tool error, continue with empty findings

**Display progress**:
```markdown
## Running Security Analysis...

**Tool 1/2**: Slither (static analysis)
✓ Completed: [XX] findings ([XX]s)
```

### 2. Run Mythril (if available)

```bash
cd contracts
timeout 300 myth analyze [contract-path] -o json > ../.audit/raw/${AUDIT_ID}-mythril.json
```

**Track execution**:
- Start time
- Monitor for timeout (300s from config)
- Capture exit code
- Parse JSON output

**Handle errors gracefully**:
- If Mythril not installed: Skip, note in report
- If timeout: Use partial results, note in report
- If error: Continue with Slither only

**Display progress**:
```markdown
**Tool 2/2**: Mythril (symbolic execution)
✓ Completed: [XX] findings ([XXX]s)

**Total findings**: [XX] (Slither: [XX], Mythril: [XX])
**Execution time**: [X] minutes [XX] seconds

Proceeding to analysis...
```

### 3. Parse Raw Findings

Read Slither JSON from `.audit/raw/${AUDIT_ID}-slither.json`:
- Extract detector name, severity, confidence, description
- Extract file location, line numbers, function name
- Extract code snippet

Read Mythril JSON (if exists) from `.audit/raw/${AUDIT_ID}-mythril.json`:
- Extract issue title, severity, description
- Extract source location
- Extract transaction sequence

**Normalize findings** to common format:
```json
{
  "finding_id": "SLITHER-001",
  "tool": "slither",
  "detector": "reentrancy-eth",
  "severity": "medium",
  "confidence": "high",
  "title": "Reentrancy in withdrawTreasury()",
  "description": "...",
  "location": {
    "file": "contracts/src/GliskNFT.sol",
    "line_start": 245,
    "line_end": 250,
    "function": "withdrawTreasury"
  },
  "code_snippet": "..."
}
```

---

## Phase 2: Analysis

### Step 1: Deduplication

Compare findings across tools:
- Same file + same line range + similar description = duplicate
- Keep highest severity version
- Track merged count

Display:
```markdown
## Analyzing Findings ([XX] total)

**Step 1/5**: Deduplication
→ Merged [X] duplicate findings across tools
→ [XX] unique findings remain
```

### Step 2: False Positive Detection

For each finding, check against false positive patterns from config:

Load patterns from `.audit/config.json` → `false_positive_patterns`

**Matching algorithm**:
```
for finding in findings:
  for pattern in patterns:
    if pattern.tool == finding.tool AND pattern.detector == finding.detector:
      check all pattern.conditions:
        - "modifier_present": Check if code has modifier (nonReentrant, onlyOwner, etc.)
        - "state_change_before_call": Check if state updated before external call
        - "library_code": Check if source is OpenZeppelin library
        - "no_state_change_after_call": Check if no state changes after call

      if all conditions match:
        finding.is_false_positive = true
        finding.auto_dismiss = pattern.auto_dismiss
        finding.fp_explanation = pattern.explanation
```

**Context needed for matching**:
- Read code snippet to check for modifiers
- Read function body to check state change order
- Check import statements to identify OpenZeppelin usage

Display:
```markdown
**Step 2/5**: False Positive Detection
→ Auto-dismissed [XX] findings (OpenZeppelin patterns, protected functions)
→ [X] findings require deeper analysis
```

### Step 3: INoT Multi-Perspective Analysis

For findings NOT auto-dismissed as false positives:

**Load INoT config** from `.audit/config.json` → `inot_analysis`:
- 3 perspectives: Security Expert, Code Analyst, Beginner Translator
- Confidence threshold: 70
- Require agreement: 2 of 3

**For each finding, perform 3-perspective analysis**:

```markdown
You are analyzing a smart contract security finding. Use three internal perspectives to reach a final judgment.

**Finding Details**:
- Tool: [tool name]
- Detector: [detector name]
- Severity: [severity]
- Title: [title]
- Description: [description]
- Location: [file]:[line_start]-[line_end] in function [function_name]
- Code:
```solidity
[code_snippet]
```

**Known False Positive Patterns**:
[List patterns from config that might apply]

---

**Perspective 1 - Security Expert**:
Assess this finding as a security expert:
- What vulnerability class is this? (reentrancy, access control, overflow, etc.)
- What's the worst-case exploit scenario?
- Has this pattern caused real exploits historically?
- Severity assessment: Is the tool's severity accurate?

**Perspective 2 - Code Analyst**:
Analyze the actual code protections:
- What security modifiers are present? (nonReentrant, onlyOwner, onlyRole, etc.)
- What's the actual state change order? (before/after external calls)
- Is this OpenZeppelin library code or custom code?
- Does this match any known-safe patterns?
- Are there compensating controls?

**Perspective 3 - Beginner Translator**:
Explain this in terms a developer with zero security expertise can understand:
- What does this finding actually mean in plain English?
- Why should they care (or not care)?
- What specific action should they take? (fix/review/accept/ignore)
- If it's safe, explain WHY it's safe in simple terms
- If it's dangerous, explain HOW to fix it with code example

---

**Synthesis**:
Based on all three perspectives, provide:

1. **is_false_positive**: true or false
2. **confidence_score**: 0-100 (based on agreement between perspectives)
   - High confidence (90-100): All 3 perspectives strongly agree
   - Medium confidence (70-89): 2 of 3 perspectives agree
   - Low confidence (0-69): Disagreement, flag for expert review
3. **reasoning**: 2-3 sentence explanation of the judgment
4. **beginner_explanation**: 3-5 sentences explaining what this means and what to do, written for someone with zero security expertise
5. **recommended_action**: fix | review | accept | ignore
6. **priority**: critical | high | medium | low | none

**Output Format** (JSON):
{
  "is_false_positive": boolean,
  "confidence_score": number,
  "reasoning": "string",
  "beginner_explanation": "string",
  "recommended_action": "fix|review|accept|ignore",
  "priority": "critical|high|medium|low|none"
}
```

**Process findings in batches of 10** to manage context:
- After each batch, save intermediate results to `.audit/findings/${AUDIT_ID}-findings.json`
- If total findings > 50, summarize informational findings to save context

Display progress:
```markdown
**Step 3/5**: INoT Multi-Perspective Analysis

Analyzing finding 1/[X]: [title]

**Security Concern**: [summary]
**Code Analysis**: [summary]
**Beginner Translation**: [summary]
**Confidence**: [XX]%

[Continue for remaining findings...]
```

### Step 4: Coverage Cross-Reference

Read test coverage data from forge coverage output:
- Identify untested lines in the audited contract
- Cross-reference findings with untested code
- Flag findings in untested code as higher risk

Display:
```markdown
**Step 4/5**: Coverage Cross-Reference
→ Checking untested code paths...
→ All security-critical functions have test coverage
→ [X] view functions untested (acceptable, read-only)
```

### Step 5: Security Score Calculation

**Load scoring config** from `.audit/config.json` → `security_score`:
- Weights: critical=0.40, high=0.30, medium=0.15, coverage=0.10, best_practices=0.05
- Deductions: critical=100, high=50, medium=20, low=5

**Count issues by severity** (excluding auto-dismissed false positives):
- Critical: [count]
- High: [count]
- Medium: [count]
- Low: [count]

**Calculate component scores**:
```
critical_score = 100 - (critical_count * 100)
critical_score = max(0, critical_score)  // floor at 0

high_score = 100 - (high_count * 50)
high_score = max(0, high_score)

medium_score = 100 - (medium_count * 20)
medium_score = max(0, medium_score)

coverage_score = test_coverage_percentage

best_practices_score = 100  // default, deduct if anti-patterns found
```

**Calculate weighted total**:
```
security_score = (critical_score * 0.40) +
                 (high_score * 0.30) +
                 (medium_score * 0.15) +
                 (coverage_score * 0.10) +
                 (best_practices_score * 0.05)

security_score = round(security_score, 0)  // round to integer
```

**Determine deployment readiness**:
```
deployment_ready_threshold = 90  // from config

if security_score >= deployment_ready_threshold AND critical_count == 0 AND high_count == 0:
  deployment_ready = true
else:
  deployment_ready = false
```

Display:
```markdown
**Step 5/5**: Security Score Calculation
- Critical ([X] issues): +[XX] points
- High ([X] issues): +[XX] points
- Medium ([X] issues): +[XX] points
- Test Coverage ([XX]%): +[XX] points
- Best Practices: +[X] points
→ **Total: [XX]/100**

Analysis complete. Generating report...
```

---

## Phase 3: Report Generation

### 1. Create Audit Run JSON

Write to `.audit/history/{contract-name}/${AUDIT_ID}-audit.json`:

```json
{
  "audit_id": "[AUDIT_ID]",
  "contract_path": "[contract-path]",
  "contract_name": "[contract-name]",
  "started_at": "[ISO8601 timestamp]",
  "completed_at": "[ISO8601 timestamp]",
  "duration_seconds": [total seconds],
  "tools_executed": [
    {
      "tool": "slither",
      "version": "[version]",
      "exit_code": 0,
      "duration_seconds": [seconds],
      "output_file": ".audit/raw/[AUDIT_ID]-slither.json"
    },
    {
      "tool": "mythril",
      "version": "[version or null]",
      "exit_code": 0,
      "duration_seconds": [seconds or null],
      "output_file": ".audit/raw/[AUDIT_ID]-mythril.json"
    }
  ],
  "contract_metrics": {
    "lines_of_code": [number],
    "functions": [estimated],
    "external_calls": [estimated],
    "state_variables": [estimated]
  },
  "test_coverage": {
    "line_coverage_percent": [number],
    "branch_coverage_percent": [number or null],
    "coverage_report_path": "contracts/coverage-report.txt"
  },
  "findings_summary": {
    "total": [number],
    "by_severity": {
      "critical": [count],
      "high": [count],
      "medium": [count],
      "low": [count],
      "informational": [count]
    },
    "false_positives": [count],
    "actionable": [count]
  },
  "security_score": [score],
  "deployment_ready": [boolean],
  "report_path": ".audit/reports/[contract-name]/[AUDIT_ID]-audit-report.md"
}
```

### 2. Generate Markdown Report

Write to `.audit/reports/{contract-name}/${AUDIT_ID}-audit-report.md`:

```markdown
# Security Audit Report: [ContractName].sol

**Audit ID**: [AUDIT_ID]
**Date**: [YYYY-MM-DD HH:MM]
**Contract**: [contract-path] ([XXX] lines)
**Tools**: Slither v[version], Mythril v[version or N/A]

---

## Executive Summary

[✅ **Deployment Ready** | ⚠️ **Review Required** | ❌ **Not Ready**]

**Security Score**: [XX]/100

**Overall Assessment**: [2-3 sentence summary based on score and findings]
- Score 95-100: "Contract is secure and ready for deployment"
- Score 85-94: "Contract is generally secure with minor issues to review"
- Score 70-84: "Contract needs review and fixes before deployment"
- Score < 70: "Contract has significant security issues requiring immediate attention"

**Key Findings**:
- [✅/⚠️/❌] [X] critical vulnerabilities
- [✅/⚠️/❌] [X] high-severity issues
- [⚠️/ℹ️] [X] medium-severity findings
- [ℹ️] [X] informational findings

**Test Coverage**:
- Line Coverage: [XX]%
- Branch Coverage: [XX]% [or N/A]

---

## Detailed Findings

### Critical Issues: [count]

[If count = 0:]
No critical vulnerabilities found.

[For each critical finding:]
#### [N]. [Title] ❌ CRITICAL

**Location**: `[file]:[line_start]-[line_end]`

**What We Found**:
[Description from tool]

**Code**:
```solidity
[code_snippet with line numbers]
```

**Why This is Dangerous**:
[Beginner explanation from INoT]

**How to Fix**:
[Specific actionable guidance]

**Action**: 🛑 **FIX IMMEDIATELY** - Do not deploy until fixed

**Learn More**:
- [Relevant references from SWC Registry, OpenZeppelin docs, etc.]

---

### High Severity: [count]

[Same format as Critical]

---

### Medium Severity: [count]

[For each medium finding:]
#### [N]. [Title] [✅ FALSE POSITIVE | ⚠️ REVIEW NEEDED]

**Location**: `[file]:[line_start]-[line_end]`

**What [Tool] Found**:
[Description]

**Code**:
```solidity
[code_snippet]
```

[If false positive:]
**Why This is Safe**:
[Beginner explanation of why it's a false positive]

**Action**: ✅ **No action needed** - [Explanation]

[If real issue:]
**Why This Matters**:
[Beginner explanation]

**How to Fix**:
[Actionable guidance]

**Action**: ⚠️ **Review recommended** - [Explanation]

**Learn More**:
- [References]

---

### Low Severity: [count]

[Summarized or collapsed section with brief descriptions]

---

### Informational: [count]

[Brief summary, full details in separate section if needed]

---

## Security Score Breakdown

| Category | Score | Weight | Contribution |
|----------|-------|--------|--------------|
| Critical Issues ([X]) | [XXX] | 40% | [XX] |
| High Issues ([X]) | [XXX] | 30% | [XX] |
| Medium Issues ([X]) | [XXX] | 15% | [XX] |
| Test Coverage ([XX]%) | [XXX] | 10% | [XX] |
| Best Practices | [XXX] | 5% | [XX] |
| **Total** | | | **[XX]/100** |

---

## Deployment Readiness Checklist

[✅/❌] No critical vulnerabilities
[✅/❌] No high-severity vulnerabilities
[✅/⚠️/❌] Medium-severity issues reviewed and accepted
[✅/⚠️/❌] Test coverage > 80%
[✅/⚠️] Follows OpenZeppelin best practices
[✅/⚠️] Access control properly implemented
[✅/⚠️] Reentrancy protection in place

**Status**: [✅ READY FOR TESTNET DEPLOYMENT | ⚠️ REVIEW REQUIRED | ❌ NOT READY]

**Recommended Next Steps**:
1. [Action based on findings]
2. [Action based on findings]
3. Consider professional audit before mainnet (Trail of Bits, ConsenSys, OpenZeppelin)

---

## Tools Used

- **Slither** v[version] - Static analysis ([XX] seconds)
- **Mythril** v[version or N/A] - Symbolic execution ([XX] minutes [XX] seconds or N/A)

**Total Audit Time**: [X] minutes [XX] seconds

---

## References

- OWASP Smart Contract Top 10
- ConsenSys Smart Contract Best Practices
- OpenZeppelin Contracts Security Guidelines
- Trail of Bits Building Secure Contracts
- SWC Registry (Smart Contract Weakness Classification)

---

*Generated by GLISK Audit Framework v1.0.0*
*Audit ID: [AUDIT_ID]*
```

### 3. Display Summary to User

```markdown
# Comprehensive Audit Complete: [ContractName].sol

[✅ **Deployment Ready** | ⚠️ **Review Required** | ❌ **Not Ready**]

**Security Score**: [XX]/100

## Executive Summary

[Overall assessment]

**Key Findings**:
- [Icon] [X] critical vulnerabilities
- [Icon] [X] high-severity issues
- [Icon] [X] medium-severity findings
- [Icon] [X] informational findings

**Test Coverage**: [XX]% line coverage

**Full Report**: `.audit/reports/[contract-name]/[AUDIT_ID]-audit-report.md`

**Audit History**:
[Check if previous audits exist in .audit/history/[contract-name]/]
- This is audit #[X] for this contract
[If previous exists:]
- Previous score: [XX]/100 ([date])
- Trend: [📈 Improving / → Stable / 📉 Degrading] ([+/-]X points)

**Next Steps**:
1. [Most important action based on findings]
2. [Second action]
3. [Third action]

---

**Tools Used**:
- Slither v[version] ([XX] seconds)
- Mythril v[version] ([XX] minutes)

**Total Time**: [X] minutes [XX] seconds
```

---

## Error Handling

Throughout the audit, handle these common errors gracefully:

### Missing Dependencies
```markdown
❌ **Error**: Slither not found

**Installation Options**:

Option 1 (Recommended): Ephemeral execution
```bash
uvx --from slither-analyzer slither --version
```

Option 2: Global installation
```bash
pip3 install slither-analyzer
```

**After installing, retry**: `/audit [contract-path]`
```

### Compilation Failures
```markdown
❌ **Error**: Contract compilation failed

**Issue**: [Show forge build output]

**Common Fixes**:
1. Install dependencies: `cd contracts && forge install`
2. Check remappings: Verify `remappings.txt` has correct paths
3. Update dependencies: `forge update`
4. Clean build: `forge clean && forge build`

**After fixing, retry**: `/audit [contract-path]`
```

### Tool Timeouts
```markdown
⏱️ **Warning**: Mythril exceeded 5-minute timeout

**What happened**: Mythril analysis did not complete within the configured timeout.

**Options**:
1. **Continue with partial results**: Audit report includes Slither findings only
2. **Increase timeout**: Edit `.audit/config.json` and increase `tools.mythril.timeout_seconds`
3. **Simplify contract**: Complex loops may cause timeouts - consider refactoring

**Current Status**: Proceeding with Slither results. Report will note incomplete Mythril analysis.
```

### Contract Size Exceeded
```markdown
❌ **Error**: Contract exceeds size limit

**Contract Size**: [XXXX] lines
**Maximum Allowed**: 1500 lines (configured in `.audit/config.json`)

**Why This Matters**:
- Automated tools may timeout or produce incomplete results on very large contracts
- Large contracts are harder to audit comprehensively
- Security review quality decreases with contract size

**Recommended Actions**:
1. **Split contract**: Refactor into smaller, focused contracts
2. **Extract libraries**: Move reusable code to separate libraries
3. **Professional audit**: For contracts > 1500 lines, consider hiring professional auditors

**To override** (not recommended): Edit `.audit/config.json` → `thresholds.max_contract_lines`
```

---

## Context Management

If processing a large number of findings (> 50):

1. **Batch processing**: Process findings in groups of 10
2. **Save intermediate progress**: Write to `.audit/findings/${AUDIT_ID}-findings.json` after each batch
3. **Summarize informational findings**: Group low-priority findings by type
4. **Prioritize critical/high**: Always provide full analysis for serious issues

If context window approaching limit:
```markdown
⚠️ **Context Limit Warning**: Large number of findings detected

**Strategy**: Processing findings in batches
- Critical and High severity: Full INoT analysis
- Medium severity: Full INoT analysis
- Low and Informational: Grouped summary

**Progress saved to**: `.audit/findings/${AUDIT_ID}-findings.json`

Continuing analysis...
```

---

## Configuration Reference

All behavior is controlled by `.audit/config.json`:
- Tool paths and timeouts
- False positive patterns
- INoT analysis settings
- Security score weights
- Report format options

To customize audit behavior, edit this file before running `/audit`.

---

**Audit Command Version**: 1.0.0
**Last Updated**: 2025-10-13
