# Command Specification: Audit Framework

**Feature**: 002-smart-contract-audit
**Purpose**: Define slash command contracts for audit workflow

## Command Overview

The audit framework provides 2 slash commands:

1. `/audit` - Main comprehensive audit command (Slither + Mythril, 3-5min)
2. `/audit.report` - View or regenerate audit reports and history

---

## 1. /audit (Comprehensive Audit)

**Purpose**: Run comprehensive security audit using multiple tools

**Usage**:
```bash
/audit [contract-path]
/audit                          # Auto-detect from current directory
/audit contracts/src/GliskNFT.sol
```

**Workflow** (spec-kit pattern with phases):

### Phase 0: Prerequisites
```markdown
## Prerequisites Check

- [X] Foundry installed: forge 0.2.0
- [X] Contract compiles: build successful
- [X] Tests pass: all 109 tests passing
- [X] Test coverage: 100% line coverage
- [X] Slither available: 0.10.4 (via uvx)
- [X] Mythril available: 0.24.1

**Contract Info**:
- Path: contracts/src/GliskNFT.sol
- Size: 723 lines
- Within limits: ✅ (max 1500 lines)

**Proceeding with comprehensive audit...**
```

**Error Handling**:
- If contract not found → List available contracts in `contracts/src/`
- If compilation fails → Show forge error with suggested fixes
- If tests fail → Warn but allow audit (note in report)
- If Slither/Mythril missing → Provide installation commands
- If contract > 1500 lines → Error with guidance to split or get professional audit

### Phase 1: Scan
```markdown
## Running Security Analysis...

**Tool 1/2**: Slither (static analysis)
[=====>    ] Running... (18s / 30s timeout)
✓ Completed: 33 findings

**Tool 2/2**: Mythril (symbolic execution)
[===>      ] Running... (145s / 300s timeout)
✓ Completed: 14 findings

**Total findings**: 47 (Slither: 33, Mythril: 14)
**Execution time**: 4 minutes 23 seconds

Proceeding to analysis...
```

**Implementation Notes**:
- Execute tools sequentially (Slither first, then Mythril)
- Save raw JSON outputs to `.audit/raw/{contract}-{timestamp}-{tool}.json`
- Parse findings into structured format
- Create Audit Run entity with status: Completed

### Phase 2: Analyze
```markdown
## Analyzing Findings (47 total)

**Step 1/5**: Deduplication
→ Merged 6 duplicate findings across tools
→ 41 unique findings remain

**Step 2/5**: False Positive Detection
→ Auto-dismissed 35 findings (OpenZeppelin patterns, protected functions)
→ 6 findings require deeper analysis

**Step 3/5**: INoT Multi-Perspective Analysis

Analyzing finding 1/6: Reentrancy in withdrawTreasury()

**Perspective 1 - Security Concern**:
- Vulnerability class: Reentrancy
- Worst-case exploit: Attacker could drain treasury
- Historical exploits: DAO hack (2016, $50M)

**Perspective 2 - Context Analysis**:
- Protection present: nonReentrant modifier (OpenZeppelin)
- State changes: Balance cleared BEFORE external call
- Access control: DEFAULT_ADMIN_ROLE required
- Pattern match: Checks-Effects-Interactions ✓

**Perspective 3 - Beginner Translation**:
- **Status**: ✅ Safe (False Positive)
- **Why**: Function has triple protection:
  1. nonReentrant modifier blocks reentrancy
  2. State updated before sending ETH
  3. Only admin can call
- **Action**: No changes needed
- **Confidence**: 95%

[Continue for remaining 5 findings...]

**Step 4/5**: Coverage Cross-Reference
→ Checking untested code paths...
→ All security-critical functions have test coverage
→ 2 view functions untested (acceptable, read-only)

**Step 5/5**: Security Score Calculation
- Critical (0 issues): +40 points
- High (0 issues): +30 points
- Medium (1 needs review): +12 points (3pt deduction)
- Test Coverage (100%): +10 points
- Best Practices: +5 points
→ **Total: 97/100**

Analysis complete. Generating report...
```

**Context Management**:
- Process findings in batches of 10
- Save intermediate analysis after each batch
- If total findings > 50: Summarize informational findings
- If context approaching limit: Save progress to `.audit/findings/{contract}-{timestamp}-findings.json`

**INoT Implementation**:
Prompt structure for each finding:
```
You are analyzing a smart contract security finding. Use three perspectives:

1. **Security Expert**: Assess vulnerability severity and exploit scenarios
2. **Code Analyst**: Evaluate actual protections and patterns in the code
3. **Beginner Translator**: Explain in simple terms what this means and what to do

Finding: [tool output]
Code context: [relevant code snippet]
Known patterns: [false positive patterns from config]

Provide:
- is_false_positive: true/false
- confidence_score: 0-100
- reasoning: brief explanation
- beginner_explanation: actionable guidance
- recommended_action: fix/review/accept/ignore
```

### Phase 3: Report
```markdown
# Comprehensive Audit Complete: GliskNFT.sol

✅ **Deployment Ready**: Yes
**Security Score**: 97/100

## Executive Summary

GliskNFT.sol is secure and ready for testnet deployment. The contract follows industry best practices for NFT implementations.

**Key Findings**:
- ✅ 0 critical vulnerabilities
- ✅ 0 high-severity issues
- ⚠️  1 medium-severity issue (recommended for review)
- ℹ️  40 informational findings (optimizations, false positives)

**Test Coverage**: 100% line coverage, 98.5% branch coverage

**Full Report**: `.audit/reports/glisknft/2025-10-13T14-30-00-audit-report.md`

**Audit History**:
- This is audit #3 for this contract
- Previous score: 95/100 (2025-10-10)
- Trend: 📈 Improving (+2 points)

**Next Steps**:
1. Review medium-severity finding (access control in setMintPrice)
2. Deploy to Base Sepolia testnet
3. Run integration tests
4. Consider professional audit before mainnet

---

**Tools Used**:
- Slither v0.10.4 (18 seconds)
- Mythril v0.24.1 (4 min 5 sec)

**Total Time**: 4 minutes 23 seconds
```

**Performance Target**: 3-5 minutes total for 500-1500 LOC contracts

---

## 2. /audit.report (Report Viewer)

**Purpose**: View or regenerate audit reports and history

**Usage**:
```bash
/audit.report [contract-name]                    # View latest report
/audit.report [contract-name] --list             # List all reports
/audit.report [contract-name] --audit-id [id]    # View specific report
/audit.report [contract-name] --compare [id1] [id2]  # Compare two audits
```

**Behavior**:

### Default (View Latest)
```markdown
# Latest Audit Report: GliskNFT.sol

**Audit ID**: glisknft-2025-10-13T14-30-00
**Date**: 2025-10-13 14:30
**Security Score**: 97/100

## Quick Summary

✅ Deployment Ready
- 0 critical issues
- 0 high-severity issues
- 1 medium-severity issue (recommended for review)

**View Full Report**:
`.audit/reports/glisknft/2025-10-13T14-30-00-audit-report.md`

**Commands**:
- `/audit.report glisknft --list` - View all historical reports
- `cat .audit/reports/glisknft/2025-10-13T14-30-00-audit-report.md` - Read full report
- `/audit contracts/src/GliskNFT.sol` - Run new audit
```

### List Mode
```markdown
# Audit History: GliskNFT.sol

| Date | Score | Status | Findings | Report |
|------|-------|--------|----------|--------|
| 2025-10-13 14:30 | 97/100 | ✅ Ready | 1 medium | [View](.audit/reports/glisknft/2025-10-13T14-30-00-audit-report.md) |
| 2025-10-10 16:45 | 95/100 | ✅ Ready | 2 medium | [View](.audit/reports/glisknft/2025-10-10T16-45-00-audit-report.md) |
| 2025-10-08 09:15 | 92/100 | ⚠️ Review | 1 high, 2 medium | [View](.audit/reports/glisknft/2025-10-08T09-15-00-audit-report.md) |

**Trend**: 📈 Improving (92 → 95 → 97)

**Analysis**:
- Audit #1 (Oct 8): High-severity reentrancy issue identified
- Audit #2 (Oct 10): High issue fixed, 2 medium remain
- Audit #3 (Oct 13): 1 medium fixed, 1 new medium (access control)

**Recommendation**: Current state is deployment-ready. The remaining medium-severity finding is a design consideration, not a critical vulnerability.
```

### Compare Mode
```markdown
## Comparing Audits: GliskNFT.sol

**Audit A**: 2025-10-10 16:45 (Score: 95/100)
**Audit B**: 2025-10-13 14:30 (Score: 97/100)

### Changes

**Fixed** (2 issues):
1. ✅ Medium: Reentrancy in claimAuthorRewards() - Added nonReentrant modifier
2. ✅ Medium: Missing input validation in setMintPrice() - Added require statement

**New** (1 issue):
1. ⚠️  Medium: Role-based access control pattern in setMintPrice() - Consider using more granular roles

**Unchanged** (38 findings):
- 38 informational findings (library code, optimizations)

### Summary

**Score Change**: +2 points (95 → 97)
**Risk Level**: Reduced (2 medium issues fixed)
**Status**: Both audits show deployment-ready status

The new medium-severity finding is a design consideration identified by improved analysis, not a regression. The contract's security posture has improved.
```

---

## Command Implementation Location

**Target Directory**: `.claude/commands/`

**Files to Create**:
```
.claude/commands/
├── audit.md                    # Main comprehensive audit
└── audit.report.md             # Report viewer and history
```

**Command File Format**:
Each file contains a markdown document that defines the command prompt and workflow that Claude Code will execute.

---

## Error Handling Standards

### Graceful Degradation
```markdown
⚠️ **Warning**: Mythril not found

Continuing with Slither-only analysis. Results will be less comprehensive.

**To install Mythril**:
```bash
pip3 install mythril
```

**Note**: Comprehensive audits require both Slither and Mythril. Consider installing Mythril for full coverage.
```

### User-Friendly Errors
```markdown
❌ **Error**: Contract compilation failed

**Issue**: Missing import in GliskNFT.sol:5
```solidity
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
         ^ Import path not found
```

**Fix**:
1. Run `forge install` to install dependencies
2. Check `remappings.txt` for correct import paths
3. Run `forge build` to verify

**After fixing, retry**: `/audit contracts/src/GliskNFT.sol`
```

### Timeout Handling
```markdown
⏱️ **Tool Timeout**: Mythril exceeded 5-minute limit

**What happened**: Mythril analysis did not complete within the timeout period.

**Options**:
1. **View partial results**: Audit completed with Slither findings only
2. **Increase timeout**: Edit `.audit/config.json`:
   ```json
   {
     "tools": {
       "mythril": {
         "timeout_seconds": 600
       }
     }
   }
   ```
3. **Simplify contract**: Complex loops can cause timeouts - consider refactoring

**Current Status**: Report generated with Slither findings. Security score may be conservative without Mythril analysis.
```

---

## Security & Privacy

**Data Storage**:
- All audit data stored locally in `.audit/` (gitignored by default)
- No data sent to external services
- Slither and Mythril run locally
- Reports can be committed to git (user choice)

**Sensitive Information**:
- Contract source code never leaves local machine
- No wallet addresses or private keys in reports
- Only checksummed addresses shown if needed

---

## Future Enhancements (Out of Scope for MVP)

These are noted for future development but not part of current implementation:

- `/audit.fix` - AI-suggested fixes for findings
- `/audit.ci` - Generate CI/CD integration scripts
- `/audit.export` - Export reports to PDF/HTML
- `/audit.trends` - Visualize security metrics over time
- `/audit.compare --diff` - Show code diff between audits

---

**Version**: 1.0
**Last Updated**: 2025-10-13 (Simplified to single comprehensive mode)
