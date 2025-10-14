# Quick Start: Smart Contract Audit Framework

**Feature**: 002-smart-contract-audit
**Purpose**: Practical guide for using the audit framework

## Overview

The GLISK Audit Framework provides automated security validation for Solidity smart contracts through simple slash commands. Designed for developers with zero security expertise.

**What it does**:
- Runs industry-standard security tools (Slither, Mythril)
- Interprets findings with beginner-friendly explanations
- Provides clear deployment readiness decisions
- Tracks audit history and trends

**What it doesn't do**:
- Replace professional security audits
- Detect business logic vulnerabilities
- Audit off-chain code (backend/frontend)

---

## Installation

### Prerequisites

1. **Foundry** (required):
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
forge --version  # Should show v0.2.0 or newer
```

2. **Slither** (required for fast/comprehensive mode):
```bash
# Option 1: Ephemeral execution (recommended)
uvx --from slither-analyzer slither --version

# Option 2: Global installation
pip3 install slither-analyzer
slither --version
```

3. **Mythril** (optional, for comprehensive mode only):
```bash
pip3 install mythril
myth version
```

### Setup

1. Ensure your contract compiles:
```bash
cd contracts
forge build
```

2. Run tests (recommended):
```bash
forge test
```

3. Ready to audit!

---

## Basic Usage

### Scenario 1: First-Time Audit

**When**: Before testnet/mainnet deployment, or to validate security of completed contract

**Command**:
```bash
/audit contracts/src/GliskNFT.sol
```

**What happens**:
1. ✓ Prerequisites check (30 seconds)
2. ✓ Run Slither + Mythril (3-5 minutes)
3. ✓ Analyze 40+ findings with INoT (1 minute)
4. ✓ Generate report (10 seconds)

**Expected output**:
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
```

### Scenario 2: View Latest Report

**When**: Check current security status without re-running audit

**Command**:
```bash
/audit.report glisknft
```

**Output**:
```markdown
# Latest Audit: GliskNFT.sol

**Date**: 2025-10-13 15:45
**Mode**: Comprehensive
**Score**: 96/100

✅ Deployment Ready

**View full report**:
`.audit/reports/glisknft/2025-10-13T15-45-00-audit-report.md`
```

---

## Real-World Examples

### Example 1: GliskNFT.sol (ERC-721 Contract)

**Context**: 723-line NFT contract with payment splitting, season lifecycle, and royalties

**Running Audit**:
```bash
/audit contracts/src/GliskNFT.sol
```

**Results**:
```markdown
## Audit Summary

**Total Findings**: 47 (Slither: 33, Mythril: 14)

### Breakdown:
- **Critical**: 0
- **High**: 0
- **Medium**: 3
  1. Reentrancy in withdrawTreasury() → ✅ False positive (nonReentrant modifier)
  2. Reentrancy in mint() → ✅ False positive (nonReentrant modifier)
  3. Arbitrary send in withdrawTreasury() → ✅ False positive (admin-only)
- **Low**: 4 (all library code warnings)
- **Info**: 40 (optimization suggestions)

### Key Learnings:

**Finding**: "Reentrancy in withdrawTreasury()"
**Beginner Explanation**:
Slither flagged this function because it sends ETH after changing state. However, this is actually safe because:

1. ✅ `nonReentrant` modifier prevents reentrancy attacks
2. ✅ State cleared BEFORE sending ETH (checks-effects-interactions pattern)
3. ✅ Only admin can call (access control)

**Code**:
```solidity
function withdrawTreasury() external onlyRole(DEFAULT_ADMIN_ROLE) nonReentrant {
    uint256 amount = treasuryBalance;
    treasuryBalance = 0;  // ← Cleared first
    (bool success,) = msg.sender.call{value: amount}();  // ← Then send
    require(success, "Transfer failed");
}
```

**No action needed** - this follows best practices!

**Security Score**: 97/100
**Deployment**: ✅ Ready for testnet
**Execution Time**: 4 minutes 23 seconds
```

**Follow-Up Audit** (after code changes):
```bash
/audit contracts/src/GliskNFT.sol
```

**Results**:
```markdown
## Audit Complete: GliskNFT.sol

**Security Score**: 97/100 (unchanged from last audit)

**Changes since last audit** (2025-10-10):
- Modified: `setMintPrice()` function
- Added: Additional access control validation

**New Findings**: 0
**Status**: ✅ No new security issues detected

**Audit History**:
- This is audit #4 for this contract
- Previous score: 97/100 (2025-10-13)
- Trend: → Stable

✅ Contract remains deployment-ready!
```

---

### Example 2: Handling Issues

**Scenario**: Audit finds a real vulnerability

**Command**:
```bash
/audit contracts/src/TokenSale.sol
```

**Output**:
```markdown
# Comprehensive Audit: TokenSale.sol

⚠️ **Action Required**
**Security Score**: 72/100

## Critical Issues: 1

### 1. Unprotected ETH Withdrawal ❌ CRITICAL

**Location**: `contracts/src/TokenSale.sol:45-48`

**What We Found**:
Anyone can call `withdraw()` and steal all ETH from the contract.

**Code**:
```solidity
function withdraw() external {
    uint256 balance = address(this).balance;
    (bool success,) = msg.sender.call{value: balance}();
    require(success);
}
```

**Why This is Dangerous**:
- No access control: ANY address can call this
- Sends all ETH to caller
- This is a **critical vulnerability** that WILL result in funds being stolen

**How to Fix**:
```solidity
// Option 1: Add onlyOwner modifier
function withdraw() external onlyOwner {
    uint256 balance = address(this).balance;
    (bool success,) = owner().call{value: balance}();
    require(success);
}

// Option 2: Use OpenZeppelin Ownable
import "@openzeppelin/contracts/access/Ownable.sol";

contract TokenSale is Ownable {
    function withdraw() external onlyOwner {
        // ... withdrawal logic
    }
}
```

**Action**: 🛑 **FIX IMMEDIATELY** - Do not deploy until fixed

**Learn More**:
- [OpenZeppelin Access Control](https://docs.openzeppelin.com/contracts/4.x/access-control)
- [SWC-105: Unprotected Ether Withdrawal](https://swcregistry.io/docs/SWC-105)

---

## Deployment: ⛔ **NOT READY**

Fix critical issue before proceeding.

**After fixing, re-run**:
```bash
/audit contracts/src/TokenSale.sol
```
```

---

## Common Workflows

### Workflow 1: Greenfield Contract Development

```bash
# 1. Write contract
# 2. Write tests
forge test

# 3. First security audit
/audit contracts/src/MyContract.sol

# 4. Fix any issues found
# 5. Add more features
# 6. Run audit again at major milestones
/audit contracts/src/MyContract.sol

# 7. Review changes from previous audit
/audit.report mycontract --list

# 8. Fix any new issues
# 9. Final audit before deployment
/audit contracts/src/MyContract.sol

# 10. Deploy to testnet
forge script script/Deploy.s.sol --rpc-url testnet --broadcast
```

### Workflow 2: Modifying Existing Contract

```bash
# 1. Check current security status
/audit.report mycontract

# 2. Make changes to contract
# 3. Run audit to validate changes
/audit contracts/src/MyContract.sol

# 4. Compare with previous audit
/audit.report mycontract --list

# 5. Review any new findings
/audit.report mycontract --compare [previous-id] [current-id]
```

### Workflow 3: Pre-Deployment Checklist

```bash
# 1. Run comprehensive audit
/audit contracts/src/MyContract.sol

# 2. Verify test coverage
forge coverage

# 3. Check deployment readiness
/audit.report mycontract

# 4. If score < 90: Review findings
cat .audit/reports/mycontract/2025-10-13T14-30-00-audit-report.md

# 5. If deployment ready: Proceed
forge script script/Deploy.s.sol --rpc-url mainnet --broadcast

# 6. Document audit in README
echo "Last audited: $(date) - Score: 97/100" >> README.md
```

---

## Understanding Reports

### Security Score Breakdown

**How it's calculated**:
```
Score = (Critical * 0.4) + (High * 0.3) + (Medium * 0.15) + (Coverage * 0.1) + (BestPractices * 0.05)

Critical: 100 - (critical_count * 100)
High:     100 - (high_count * 50)
Medium:   100 - (medium_count * 20)
Coverage: test_coverage_percentage
BestPractices: 100 if no anti-patterns, else 80
```

**Example**:
```
0 critical:  100 * 0.4 = 40 points
0 high:      100 * 0.3 = 30 points
1 medium:     80 * 0.15 = 12 points (20-point deduction)
99% coverage: 99 * 0.1 = 9.9 points
Best practices: 100 * 0.05 = 5 points
---
Total: 96.9 / 100
```

### Deployment Readiness Criteria

**✅ Ready to Deploy**:
- Security score ≥ 90
- 0 critical issues
- 0 high-severity issues
- < 3 medium-severity issues (and all reviewed)
- Test coverage ≥ 80%

**⚠️ Review Recommended**:
- Security score 70-89
- 1-2 medium-severity issues
- Test coverage 60-80%

**⛔ Not Ready**:
- Security score < 70
- Any critical or high-severity issues
- Test coverage < 60%

---

## Troubleshooting

### Issue: "Slither not found"

**Solution**:
```bash
# Try ephemeral execution
uvx --from slither-analyzer slither --version

# Or install globally
pip3 install slither-analyzer
```

### Issue: "Contract compilation failed"

**Solution**:
```bash
# Check forge build output
forge build

# Common fixes:
forge install                # Install dependencies
forge clean && forge build   # Clean build cache
```

### Issue: "Audit taking too long"

**Possible causes**:
1. **Large contract**: If > 1500 lines, consider splitting into smaller contracts
2. **Mythril timeout**: Edit `.audit/config.json` to increase timeout:
   ```json
   "tools": {
     "mythril": {
       "timeout_seconds": 600  // Increase to 10 minutes
     }
   }
   ```
3. **Complex loops**: Mythril struggles with complex loops - may timeout on loop-heavy contracts

**Workarounds**:
```bash
# If Mythril times out, the audit will continue with Slither results only
# You can check partial results:
/audit.report mycontract

# Or disable Mythril temporarily in .audit/config.json:
# "mythril": { "enabled": false }
```

### Issue: "Too many false positives"

**Solution**: False positive patterns are auto-detected for:
- OpenZeppelin library code
- Standard patterns (nonReentrant, onlyOwner, etc.)

If still seeing false positives, add patterns to `.audit/config.json`:
```json
{
  "false_positive_patterns": [
    {
      "tool": "slither",
      "detector": "my-custom-detector",
      "pattern": "my safe pattern",
      "auto_dismiss": true
    }
  ]
}
```

---

## Best Practices

### 1. Audit at Key Milestones

✅ **Do**:
- Run audits after implementing major features
- Run audits before testnet/mainnet deployment
- Track audit history to monitor security trends

❌ **Don't**:
- Wait until final deployment to run first audit
- Ignore warnings (even informational ones)
- Skip tests (test coverage affects audit quality)

### 2. Understand Findings

✅ **Do**:
- Read the "Why This Matters" sections
- Check provided references (OpenZeppelin docs, etc.)
- Ask for clarification if unsure

❌ **Don't**:
- Blindly accept "false positive" labels
- Ignore medium-severity findings
- Skip the learning opportunity

### 3. Complement with Professional Audits

✅ **Do**:
- Use automated audits for development
- Get professional audit before mainnet
- Budget $10k-30k for professional audit

❌ **Don't**:
- Rely solely on automated tools for mainnet
- Skip professional audit for high-value contracts
- Assume 100/100 score = perfectly secure

---

## Next Steps

1. **Try it**: Run your first comprehensive audit on GliskNFT.sol
   ```bash
   /audit contracts/src/GliskNFT.sol
   ```

2. **Read a report**: Open the generated report in `.audit/reports/glisknft/`

3. **Learn**: Review findings, read beginner explanations, and explore referenced documentation

4. **Integrate**: Add audit checks at key milestones in your development workflow

5. **Share**: Commit audit reports to git for team visibility and track security improvements over time

---

## Support

**Documentation**:
- Full spec: `specs/002-smart-contract-audit/spec.md`
- Data model: `specs/002-smart-contract-audit/data-model.md`
- Command reference: `specs/002-smart-contract-audit/contracts/audit-command-spec.md`

**External Resources**:
- [Slither Documentation](https://github.com/crytic/slither)
- [OpenZeppelin Security](https://docs.openzeppelin.com/contracts/4.x/api/security)
- [ConsenSys Best Practices](https://consensys.github.io/smart-contract-best-practices/)
- [SWC Registry](https://swcregistry.io/) - Vulnerability classifications

**Professional Auditors** (for mainnet):
- Trail of Bits
- ConsenSys Diligence
- OpenZeppelin Security
- Quantstamp
- Certora

---

*Built with ❤️ for GLISK Season 0*
