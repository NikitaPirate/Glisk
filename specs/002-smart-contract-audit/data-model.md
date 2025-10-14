# Data Model: Smart Contract Audit Framework

**Feature**: 002-smart-contract-audit
**Created**: 2025-10-13
**Purpose**: Define data structures for audit execution, findings, and reports

## Overview

The audit framework uses **file-based storage** with JSON for structured data and Markdown for human-readable reports. All audit data is stored in `.audit/` directory (gitignored).

---

## Entity Definitions

### 1. Audit Configuration

**Purpose**: Global settings for audit execution

**Storage**: `.audit/config.json`

**Schema**:
```json
{
  "version": "1.0.0",
  "tools": {
    "slither": {
      "enabled": true,
      "path": "uvx --from slither-analyzer slither",
      "timeout_seconds": 30
    },
    "mythril": {
      "enabled": true,
      "path": "myth",
      "timeout_seconds": 300
    }
  },
  "thresholds": {
    "audit_timeout_seconds": 300,
    "max_contract_lines": 1500,
    "max_findings_per_report": 100
  },
  "false_positive_patterns": [
    {
      "tool": "slither",
      "detector": "reentrancy-benign",
      "pattern": "nonReentrant modifier present",
      "auto_dismiss": true
    },
    {
      "tool": "slither",
      "detector": "dead-code",
      "pattern": "OpenZeppelin library function",
      "auto_dismiss": true
    }
  ],
  "report_format": {
    "include_code_snippets": true,
    "max_snippet_lines": 10,
    "beginner_friendly": true
  }
}
```

**Validation Rules**:
- `version`: Semantic version string (e.g., "1.0.0")
- `tools.*.enabled`: Boolean
- `tools.*.timeout_seconds`: Positive integer
- `thresholds.*_timeout_seconds`: Positive integer
- `thresholds.max_contract_lines`: Positive integer (recommended: 1500)
- `false_positive_patterns`: Array of pattern objects

---

### 2. Audit Run

**Purpose**: Metadata for a single audit execution

**Storage**: `.audit/history/{contract-name}/{timestamp}-audit.json`

**Schema**:
```json
{
  "audit_id": "glisknft-2025-10-13T14-30-00",
  "contract_path": "contracts/src/GliskNFT.sol",
  "contract_name": "GliskNFT",
  "started_at": "2025-10-13T14:30:00Z",
  "completed_at": "2025-10-13T14:34:45Z",
  "duration_seconds": 285,
  "tools_executed": [
    {
      "tool": "slither",
      "version": "0.10.4",
      "exit_code": 0,
      "duration_seconds": 18,
      "output_file": ".audit/raw/glisknft-2025-10-13T14-30-00-slither.json"
    },
    {
      "tool": "mythril",
      "version": "0.24.1",
      "exit_code": 0,
      "duration_seconds": 267,
      "output_file": ".audit/raw/glisknft-2025-10-13T14-30-00-mythril.json"
    }
  ],
  "contract_metrics": {
    "lines_of_code": 723,
    "functions": 28,
    "external_calls": 5,
    "state_variables": 12
  },
  "test_coverage": {
    "line_coverage_percent": 100.0,
    "branch_coverage_percent": 98.5,
    "coverage_report_path": "contracts/coverage-report.txt"
  },
  "findings_summary": {
    "total": 33,
    "by_severity": {
      "critical": 0,
      "high": 0,
      "medium": 3,
      "low": 4,
      "informational": 26
    },
    "false_positives": 30,
    "actionable": 3
  },
  "security_score": 95,
  "deployment_ready": true,
  "report_path": ".audit/reports/glisknft/2025-10-13T14-30-00-audit-report.md"
}
```

**Validation Rules**:
- `audit_id`: Unique string (format: `{contract-name}-{ISO8601-timestamp}`)
- `started_at`, `completed_at`: ISO 8601 datetime strings
- `duration_seconds`: Positive number
- `tools_executed`: Non-empty array
- `tools_executed[].exit_code`: Integer (0 = success)
- `contract_metrics.lines_of_code`: Must be ≤ `thresholds.max_contract_lines`
- `test_coverage.*_percent`: 0.0 to 100.0
- `findings_summary.by_severity.*`: Non-negative integers
- `security_score`: 0 to 100
- `deployment_ready`: Boolean

**State Transitions**:
1. **Created**: Audit run initialized, tools not yet executed
2. **Running**: Tools executing
3. **Completed**: All tools finished, findings collected
4. **Analyzed**: Findings categorized, false positives filtered
5. **Reported**: Final report generated

---

### 3. Security Finding

**Purpose**: Individual issue identified by security tools

**Storage**: Embedded in Audit Run JSON, extracted to `audit-findings.md` during analysis

**Schema**:
```json
{
  "finding_id": "SLITHER-001",
  "tool": "slither",
  "detector": "reentrancy-eth",
  "severity": "medium",
  "confidence": "high",
  "title": "Reentrancy in GliskNFT.withdrawTreasury()",
  "description": "Function sends ETH to msg.sender after state changes",
  "location": {
    "file": "contracts/src/GliskNFT.sol",
    "line_start": 245,
    "line_end": 250,
    "function": "withdrawTreasury"
  },
  "code_snippet": "function withdrawTreasury() external onlyRole(DEFAULT_ADMIN_ROLE) nonReentrant {\n    uint256 amount = treasuryBalance;\n    treasuryBalance = 0;\n    (bool success,) = msg.sender.call{value: amount}();\n    require(success, \"Transfer failed\");\n}",
  "analysis": {
    "is_false_positive": true,
    "reasoning": "Function has nonReentrant modifier AND follows checks-effects-interactions pattern (state cleared before external call). Protected by role-based access control.",
    "confidence_score": 95,
    "perspectives": {
      "security_concern": "Reentrancy risk due to external call",
      "context_analysis": "nonReentrant modifier present, state updated before call, admin-only access",
      "beginner_translation": "This is safe because the function is protected against reentrancy attacks through multiple layers: 1) nonReentrant modifier, 2) state cleared before sending ETH, 3) only admin can call it."
    }
  },
  "recommendation": {
    "action": "accept",
    "priority": "none",
    "explanation": "No action needed. This is a false positive - the code follows best practices for safe ETH transfers.",
    "references": [
      "OpenZeppelin ReentrancyGuard pattern",
      "Checks-Effects-Interactions pattern"
    ]
  }
}
```

**Validation Rules**:
- `finding_id`: Unique within audit run
- `tool`: Enum ["slither", "mythril", "manual"]
- `detector`: String (tool-specific detector name)
- `severity`: Enum ["critical", "high", "medium", "low", "informational"]
- `confidence`: Enum ["high", "medium", "low"]
- `location.file`: Valid file path
- `location.line_start`, `location.line_end`: Positive integers
- `analysis.is_false_positive`: Boolean
- `analysis.confidence_score`: 0 to 100
- `recommendation.action`: Enum ["fix", "review", "accept", "ignore"]
- `recommendation.priority`: Enum ["critical", "high", "medium", "low", "none"]

**Relationships**:
- Belongs to one Audit Run
- References one location in source code
- May reference multiple similar findings (duplicates)

---

### 4. False Positive Pattern

**Purpose**: Predefined patterns for auto-dismissing false positives

**Storage**: Embedded in `.audit/config.json`, can be extended per-project

**Schema**:
```json
{
  "pattern_id": "FP-001",
  "name": "OpenZeppelin Reentrancy Guard",
  "tool": "slither",
  "detector": "reentrancy-eth",
  "conditions": [
    {
      "type": "modifier_present",
      "value": "nonReentrant"
    },
    {
      "type": "state_change_before_call",
      "value": true
    }
  ],
  "auto_dismiss": true,
  "explanation": "Function is protected by OpenZeppelin's nonReentrant modifier and follows checks-effects-interactions pattern."
}
```

**Matching Algorithm**:
1. For each finding, check all applicable patterns (matching tool + detector)
2. Evaluate all conditions for the pattern
3. If all conditions pass, mark finding as false positive
4. If `auto_dismiss: true`, exclude from actionable findings
5. Still include in report with "False Positive" label for transparency

---

### 5. Audit Report

**Purpose**: Human-readable audit report with beginner-friendly explanations

**Storage**: `.audit/reports/{contract-name}/{timestamp}-audit-report.md`

**Structure** (Markdown):

```markdown
# Security Audit Report: GliskNFT.sol

**Audit ID**: glisknft-2025-10-13T14-30-00
**Date**: 2025-10-13
**Contract**: contracts/src/GliskNFT.sol (723 lines)
**Tools**: Slither v0.10.4, Mythril v0.24.1

---

## Executive Summary

✅ **Deployment Ready**: Yes

**Security Score**: 95/100

**Overall Assessment**: GliskNFT.sol is secure and ready for testnet deployment. All critical and high-severity issues have been addressed. The contract follows industry best practices for NFT implementations.

**Key Findings**:
- ✅ No critical or high-severity vulnerabilities
- ⚠️ 3 medium-severity findings (all false positives)
- ℹ️ 26 informational findings (optimization suggestions)

**Test Coverage**:
- Line Coverage: 100%
- Branch Coverage: 98.5%

---

## Detailed Findings

### Critical Issues: 0

No critical vulnerabilities found.

---

### High Severity: 0

No high-severity issues found.

---

### Medium Severity: 3 (all false positives)

#### 1. Reentrancy in withdrawTreasury() ✅ FALSE POSITIVE

**Location**: `contracts/src/GliskNFT.sol:245-250`

**What Slither Found**:
The function sends ETH to `msg.sender` after state changes.

**Why This is Safe**:
This is a false positive. The function is actually very secure because:

1. ✅ **nonReentrant modifier**: OpenZeppelin's guard prevents reentrancy attacks
2. ✅ **Checks-Effects-Interactions pattern**: `treasuryBalance` is set to 0 BEFORE sending ETH
3. ✅ **Access control**: Only admin can call this function

**Code**:
```solidity
function withdrawTreasury() external onlyRole(DEFAULT_ADMIN_ROLE) nonReentrant {
    uint256 amount = treasuryBalance;
    treasuryBalance = 0;  // ← State cleared FIRST
    (bool success,) = msg.sender.call{value: amount}();  // ← Then external call
    require(success, "Transfer failed");
}
```

**Action**: ✅ **No action needed** - This follows best practices.

**Learn More**:
- [OpenZeppelin ReentrancyGuard](https://docs.openzeppelin.com/contracts/4.x/api/security#ReentrancyGuard)
- [Checks-Effects-Interactions Pattern](https://docs.soliditylang.org/en/latest/security-considerations.html#use-the-checks-effects-interactions-pattern)

---

[... more findings ...]

---

## Security Score Breakdown

| Category | Score | Weight | Contribution |
|----------|-------|--------|--------------|
| Critical Issues (0) | 100 | 40% | 40 |
| High Issues (0) | 100 | 30% | 30 |
| Medium Issues (3 FP) | 100 | 15% | 15 |
| Test Coverage (99%) | 99 | 10% | 9.9 |
| Best Practices | 100 | 5% | 5 |
| **Total** | | | **95/100** |

---

## Deployment Readiness Checklist

✅ No critical vulnerabilities
✅ No high-severity vulnerabilities
✅ All medium-severity issues are false positives
✅ Test coverage > 95%
✅ Follows OpenZeppelin best practices
✅ Access control properly implemented
✅ Reentrancy protection in place

**Status**: ✅ **READY FOR TESTNET DEPLOYMENT**

**Recommended Next Steps**:
1. Deploy to Base Sepolia testnet
2. Run integration tests against deployed contract
3. Consider professional audit before mainnet (Trail of Bits, ConsenSys, OpenZeppelin)

---

## Tools Used

- **Slither** v0.10.4 - Static analysis (18 seconds)
- **Mythril** v0.24.1 - Symbolic execution (4 minutes 32 seconds)

**Total Audit Time**: 4 minutes 50 seconds

---

## References

- OWASP Smart Contract Top 10
- ConsenSys Smart Contract Best Practices
- OpenZeppelin Contracts Security Guidelines
- Trail of Bits Building Secure Contracts

---

*Generated by GLISK Audit Framework v1.0.0*
```

**Template Sections**:
1. **Executive Summary**: High-level assessment for quick decision-making
2. **Detailed Findings**: Grouped by severity, with beginner-friendly explanations
3. **Security Score**: Weighted calculation showing how score is derived
4. **Deployment Readiness Checklist**: Clear yes/no criteria
5. **Tools Used**: Transparency about analysis methods
6. **References**: Educational resources for learning

---

## File System Structure

```
.audit/
├── config.json                     # Global configuration
├── history/                        # Audit run metadata
│   └── glisknft/
│       ├── 2025-10-13T14-30-00-audit.json
│       └── 2025-10-15T10-15-00-audit.json
├── raw/                           # Raw tool outputs (for debugging)
│   ├── glisknft-2025-10-13T14-30-00-slither.json
│   ├── glisknft-2025-10-13T14-30-00-mythril.json
│   ├── glisknft-2025-10-15T10-15-00-slither.json
│   └── glisknft-2025-10-15T10-15-00-mythril.json
├── reports/                       # Human-readable reports
│   └── glisknft/
│       ├── 2025-10-13T14-30-00-audit-report.md
│       └── 2025-10-15T10-15-00-audit-report.md
└── findings/                      # Extracted findings for analysis
    ├── glisknft-2025-10-13T14-30-00-findings.json
    └── glisknft-2025-10-15T10-15-00-findings.json
```

---

## Data Flow

```
1. User runs /audit [contract-path]
   ↓
2. Create Audit Run entity (status: Created)
   ↓
3. Execute security tools: Slither + Mythril (status: Running)
   ↓
4. Collect raw outputs → .audit/raw/
   ↓
5. Parse findings from all tools → Audit Run (status: Completed)
   ↓
6. Apply false positive patterns → analyze findings
   ↓
7. INoT multi-perspective analysis → categorize findings
   ↓
8. Calculate security score → Audit Run (status: Analyzed)
   ↓
9. Generate beginner-friendly report → .audit/reports/
   ↓
10. Update Audit Run (status: Reported)
```

---

## Design Decisions

### Why File-Based Storage?

**Alternatives Considered**:
- SQLite database
- JSON document store
- In-memory only

**Chosen**: File-based storage

**Rationale**:
1. **Simplicity**: No DB setup, no schemas to migrate
2. **Transparency**: Users can inspect `.audit/` directory
3. **Portability**: Easy to share reports (just markdown files)
4. **Git-friendly**: Reports can be committed (history is gitignored)
5. **Cost**: No database overhead, fits spec-kit pattern

### Why JSON + Markdown?

**JSON** for structured data:
- Machine-readable for tooling
- Standard format, easy to parse
- Enables programmatic analysis

**Markdown** for reports:
- Human-readable, renders beautifully
- Supports code blocks, tables, links
- Can be converted to PDF/HTML if needed
- Familiar to developers

### Why Embedded Analysis in Findings?

**Alternative**: Separate analysis table/file

**Chosen**: Embed analysis within finding entity

**Rationale**:
1. **Cohesion**: Analysis is intrinsically tied to the finding
2. **Performance**: No joins needed when displaying findings
3. **Atomicity**: Update finding + analysis in single write
4. **Clarity**: All context in one place

---

## Next Phase Requirements

Phase 2 (Tasks) will need:
1. Implementation of JSON schema validation
2. File system operations (create directories, write JSON/MD)
3. False positive pattern matching algorithm
4. Security score calculation formula
5. Markdown report generation templates

All data structures defined. Ready for Phase 2: Tasks.
