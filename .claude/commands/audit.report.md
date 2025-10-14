# Audit Report Viewer

**Purpose**: View and compare security audit reports and history

**Usage**:
- `/audit.report [contract-name]` - View latest report
- `/audit.report [contract-name] --list` - List all reports
- `/audit.report [contract-name] --audit-id [id]` - View specific report
- `/audit.report [contract-name] --compare [id1] [id2]` - Compare two audits

---

## Parse Arguments

Extract from user input:
- Contract name (required): `[contract-name]`
- Mode flags: `--list`, `--audit-id`, `--compare`
- Additional parameters: audit IDs for specific modes

**Normalize contract name**: Convert to lowercase, remove `.sol` extension
Example: `GliskNFT.sol` → `glisknft`

---

## Mode 1: Default (View Latest Report)

**Usage**: `/audit.report glisknft`

### Step 1: Find Latest Audit

Check directory: `.audit/history/[contract-name]/`

```bash
ls -t .audit/history/[contract-name]/*-audit.json | head -1
```

If no audits found:
```markdown
❌ **No audits found** for contract `[contract-name]`

**Have you run an audit yet?**

Run your first audit:
```bash
/audit contracts/src/[ContractName].sol
```

**Available contracts with audit history**:
[List other contract directories in .audit/history/ if any exist]
```

### Step 2: Load Latest Audit JSON

Read `.audit/history/[contract-name]/[latest]-audit.json`

Parse:
- `audit_id`
- `completed_at` (format as readable date)
- `security_score`
- `deployment_ready`
- `findings_summary.by_severity`
- `report_path`

### Step 3: Display Summary

```markdown
# Latest Audit Report: [ContractName].sol

**Audit ID**: [audit_id]
**Date**: [YYYY-MM-DD HH:MM]
**Security Score**: [score]/100

## Quick Summary

[✅ Deployment Ready | ⚠️ Review Required | ❌ Not Ready]

**Findings**:
- [count] critical issues
- [count] high-severity issues
- [count] medium-severity issues
- [count] low/informational findings

**Test Coverage**: [XX]% line coverage

---

**View Full Report**:
```bash
cat [report_path]
```

**Other Commands**:
- `/audit.report [contract-name] --list` - View all historical reports
- `/audit contracts/src/[ContractName].sol` - Run new audit
```

---

## Mode 2: List All Reports

**Usage**: `/audit.report glisknft --list`

### Step 1: Find All Audits

List all audit JSONs for contract:
```bash
ls -t .audit/history/[contract-name]/*-audit.json
```

Parse each JSON to extract:
- Date
- Security score
- Deployment status
- Key findings (counts by severity)
- Report path

### Step 2: Check Audit Count Limit

Load config: `.audit/config.json`

If audit history limit configured (e.g., 10 audits max):
- Show only most recent 10
- Note if older audits were cleaned up

### Step 3: Calculate Trend

Compare scores across audits:
- Latest vs previous: score delta
- Overall direction: improving / stable / degrading

**Trend indicators**:
- Improving: Score increased by 5+ points
- Stable: Score changed < 5 points
- Degrading: Score decreased by 5+ points

### Step 4: Display History Table

```markdown
# Audit History: [ContractName].sol

**Total Audits**: [count]

| Date | Score | Status | Findings | Report |
|------|-------|--------|----------|--------|
| YYYY-MM-DD HH:MM | XX/100 | [✅/⚠️/❌] | [X] crit, [X] high, [X] med | [View]([report_path]) |
| YYYY-MM-DD HH:MM | XX/100 | [✅/⚠️/❌] | [X] crit, [X] high, [X] med | [View]([report_path]) |
| ... | ... | ... | ... | ... |

**Trend**: [📈 Improving / → Stable / 📉 Degrading] ([+/-]X points from [oldest] to [latest])

---

## Analysis

[Narrative summary of audit history:]
- Audit #1 ([date]): [Key issue identified]
- Audit #2 ([date]): [Issue fixed, new findings]
- Audit #3 ([date]): [Current state]

**Recommendation**: [Based on trend and current score]

---

**Commands**:
- `/audit.report [contract-name]` - View latest audit details
- `/audit.report [contract-name] --compare [id1] [id2]` - Compare two specific audits
- `/audit contracts/src/[ContractName].sol` - Run new audit
```

---

## Mode 3: Compare Two Audits

**Usage**: `/audit.report glisknft --compare audit-id-1 audit-id-2`

### Step 1: Load Both Audits

Read audit JSONs:
- `.audit/history/[contract-name]/[id1]-audit.json`
- `.audit/history/[contract-name]/[id2]-audit.json`

If either audit not found:
```markdown
❌ **Error**: Audit ID not found

**Available audits**:
[List audit IDs from --list mode]

**Usage**:
```bash
/audit.report [contract-name] --compare [audit-id-1] [audit-id-2]
```
```

Parse both JSONs to extract:
- Timestamp, score, deployment status
- Findings by severity and type
- Individual finding details (if available in stored findings JSON)

### Step 2: Determine Audit Order

Sort by timestamp:
- Earlier audit = Audit A (baseline)
- Later audit = Audit B (current)

### Step 3: Compare Findings

**Load detailed findings** (if exist):
- `.audit/findings/[id1]-findings.json`
- `.audit/findings/[id2]-findings.json`

**Categorize findings**:

**Fixed findings** (in A, not in B):
- Finding existed in Audit A
- Same finding not present in Audit B
- Match by: detector + file + line range

**New findings** (not in A, in B):
- Finding not in Audit A
- Present in Audit B

**Unchanged findings** (in both A and B):
- Same finding in both audits
- Match by: detector + file + line range

### Step 4: Calculate Deltas

**Score delta**:
```
score_change = score_B - score_A
```

**Risk level change**:
```
if (critical_B + high_B) < (critical_A + high_A):
  risk_level = "Reduced"
else if (critical_B + high_B) > (critical_A + high_A):
  risk_level = "Increased"
else:
  risk_level = "Unchanged"
```

### Step 5: Display Comparison

```markdown
## Comparing Audits: [ContractName].sol

**Audit A** (baseline): [date] (Score: [score_A]/100)
**Audit B** (current): [date] (Score: [score_B]/100)

---

### Changes

**Fixed** ([count] issues):
[For each fixed finding:]
[N]. ✅ [Severity]: [Title] - [Brief explanation of fix if available]

**New** ([count] issues):
[For each new finding:]
[N]. [⚠️/ℹ️] [Severity]: [Title] - [Brief description]

**Unchanged** ([count] findings):
- [count] critical (unchanged)
- [count] high (unchanged)
- [count] medium (unchanged)
- [count] low/informational (unchanged)

---

### Summary

**Score Change**: [+/-]X points ([score_A] → [score_B])
**Risk Level**: [Reduced / Increased / Unchanged] ([explanation])
**Deployment Status**:
- Audit A: [✅/⚠️/❌] [Status]
- Audit B: [✅/⚠️/❌] [Status]

**Analysis**:
[2-3 sentence narrative of what changed between audits]

**Interpretation**:
[Is this a regression, improvement, or lateral change? Explain why]

---

**View Full Reports**:
- Audit A: `cat [report_path_A]`
- Audit B: `cat [report_path_B]`

**Commands**:
- `/audit.report [contract-name] --list` - View all audits
- `/audit contracts/src/[ContractName].sol` - Run new audit
```

---

## Mode 4: View Specific Audit

**Usage**: `/audit.report glisknft --audit-id glisknft-2025-10-13T14-30-00`

### Step 1: Load Specific Audit

Read `.audit/history/[contract-name]/[audit-id]-audit.json`

If not found:
```markdown
❌ **Error**: Audit ID `[audit-id]` not found

**Available audits**:
[List from --list mode]
```

### Step 2: Display Details

Same as Default Mode (View Latest), but for the specified audit.

Additionally show:
```markdown
**Note**: This is a historical audit from [date].

**Latest audit**: [latest-audit-id]
View latest: `/audit.report [contract-name]`
```

---

## Audit History Management (Background)

### Cleanup Old Audits

**When**: After displaying any mode

**Load config**: `.audit/config.json` → check if history limit is set

**If limit exceeded** (e.g., > 10 audits):

1. List all audits sorted by date
2. Keep most recent N audits (from config)
3. Delete older audit JSONs from `.audit/history/[contract-name]/`
4. Delete older raw files from `.audit/raw/`
5. **Preserve** all reports in `.audit/reports/` (keep reports for documentation)

**Note to user** (if cleanup occurred):
```markdown
ℹ️ **Note**: Cleaned up old audit history. Keeping most recent 10 audits. All reports preserved in `.audit/reports/`.
```

---

## Error Handling

### No Contract Name Provided
```markdown
❌ **Error**: Contract name required

**Usage**:
```bash
/audit.report [contract-name]
/audit.report [contract-name] --list
/audit.report [contract-name] --compare [id1] [id2]
```

**Available contracts**:
[List directories in .audit/history/]
```

### Invalid Mode
```markdown
❌ **Error**: Invalid mode or arguments

**Valid modes**:
- `/audit.report [contract-name]` - View latest report
- `/audit.report [contract-name] --list` - List all reports
- `/audit.report [contract-name] --audit-id [id]` - View specific report
- `/audit.report [contract-name] --compare [id1] [id2]` - Compare two audits
```

### Contract Not Found
```markdown
❌ **Error**: No audit history found for contract `[contract-name]`

**Available contracts with audit history**:
[List directories in .audit/history/]

**To audit a new contract**:
```bash
/audit contracts/src/[ContractName].sol
```
```

---

## Helper Functions

### Format Date
Convert ISO 8601 timestamp to readable format:
- Input: `2025-10-13T14:30:00Z`
- Output: `2025-10-13 14:30` or `Oct 13, 2025 2:30 PM`

### Status Icon
Map deployment_ready boolean to icon:
- `true` → ✅ Deployment Ready
- `false` + high/critical issues → ❌ Not Ready
- `false` + only medium/low issues → ⚠️ Review Required

### Severity Summary
Format findings summary:
- `0 critical, 0 high, 2 medium` (skip zeros for cleaner output)
- Or: `✅ No critical/high issues, 2 medium`

### Trend Indicator
Based on score progression:
- Improving: 📈 Improving (+X points)
- Stable: → Stable
- Degrading: 📉 Degrading (-X points)

---

**Audit Report Viewer Version**: 1.0.0
**Last Updated**: 2025-10-13
