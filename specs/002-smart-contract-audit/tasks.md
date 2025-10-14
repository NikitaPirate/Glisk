# Tasks: Smart Contract Audit Process Framework

**Feature**: 002-smart-contract-audit
**Input**: Design documents from `/specs/002-smart-contract-audit/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete), contracts/ (complete)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **GLISK Monorepo**:
  - Slash Commands: `.claude/commands/`
  - Audit Data: `.audit/` (gitignored)
  - Contracts (audit targets): `contracts/src/`
  - Documentation: `CLAUDE.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and audit framework structure

- [X] T001 [P] Create `.audit/` directory structure with subdirectories: `history/`, `raw/`, `reports/`, `findings/`
- [X] T002 [P] Create `.audit/config.json` with default configuration (tools, thresholds, false positive patterns for OpenZeppelin)
- [X] T003 [P] Update `.gitignore` to exclude `.audit/` directory (keep audit data local)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create false positive patterns library in `.audit/config.json` with OpenZeppelin patterns (nonReentrant, onlyOwner, safe ERC721 patterns)
- [X] T005 Define INoT (Introspection of Thought) prompt templates for 3-perspective security analysis (Security Expert, Code Analyst, Beginner Translator)
- [X] T006 Create security score calculation algorithm (weighted: Critical 40%, High 30%, Medium 15%, Coverage 10%, Best Practices 5%)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Pre-deployment Security Validation (Priority: P1) 🎯 MVP

**Goal**: Comprehensive security audit that runs multiple tools (Slither, Mythril), interprets results with beginner-friendly explanations, and provides clear deployment readiness decisions

**Independent Test**: Run `/audit contracts/src/GliskNFT.sol` and verify:
- All security tools execute successfully
- Findings are analyzed with INoT multi-perspective analysis
- Report includes beginner-friendly explanations
- Clear deployment readiness decision is provided
- Execution completes in 3-5 minutes for 500-1500 line contracts

### Implementation for User Story 1

- [X] T007 [US1] Create `.claude/commands/audit.md` command file with Phase 0: Prerequisites check (Foundry, Slither, Mythril availability, contract compilation, test coverage, contract size validation)
- [X] T008 [US1] Implement Phase 1: Scan in `audit.md` - Execute Slither with timeout (30s), save raw JSON output to `.audit/raw/{contract}-{timestamp}-slither.json`
- [X] T009 [US1] Implement Phase 1: Scan (continued) - Execute Mythril with timeout (300s), save raw JSON output to `.audit/raw/{contract}-{timestamp}-mythril.json`, handle tool failures gracefully
- [X] T010 [US1] Implement Phase 2: Analyze (Step 1-2) in `audit.md` - Parse findings from tool outputs, deduplicate findings across tools, apply false positive pattern matching from config
- [X] T011 [US1] Implement Phase 2: Analyze (Step 3) - INoT multi-perspective analysis using 3 virtual agents (Security Expert, Code Analyst, Beginner Translator) for each finding, generate confidence scores and actionable recommendations
- [X] T012 [US1] Implement Phase 2: Analyze (Step 4-5) - Cross-reference findings with test coverage data, calculate security score using weighted algorithm, determine deployment readiness
- [X] T013 [US1] Implement Phase 3: Report generation - Create Audit Run JSON in `.audit/history/{contract-name}/{timestamp}-audit.json` with metadata, metrics, findings summary, security score
- [X] T014 [US1] Implement Phase 3: Report generation (continued) - Generate beginner-friendly markdown report in `.audit/reports/{contract-name}/{timestamp}-audit-report.md` following template from data-model.md (Executive Summary, Detailed Findings, Security Score Breakdown, Deployment Readiness Checklist)
- [X] T015 [US1] Add context management logic - Process findings in batches of 10, auto-summarize if > 50 findings, save intermediate progress if context approaching limit
- [X] T016 [US1] Add error handling for common scenarios: missing dependencies (provide installation commands), compilation failures (show forge errors), tool timeouts (continue with partial results), contract size exceeded (error with guidance)
- [ ] T017 [US1] Validate comprehensive audit on GliskNFT.sol contract (723 lines, ERC721 with features) - verify execution time 3-5 minutes, report accuracy, beginner-friendly explanations, security score calculation

**Checkpoint**: At this point, comprehensive security audits should be fully functional - developers can run `/audit` and get deployment readiness decisions

---

## Phase 4: User Story 2 - Audit History and Comparison (Priority: P2)

**Goal**: Track multiple audits over time, compare current security status against previous audits to understand trends, identify regressions, and validate fixes

**Independent Test**: Run multiple audits on a contract, then use `/audit.report {contract-name} --list` to verify history tracking and `/audit.report {contract-name} --compare {id1} {id2}` to verify comparison functionality

### Implementation for User Story 2

- [X] T018 [US2] Create `.claude/commands/audit.report.md` command file with default mode: View latest report - Load most recent audit from `.audit/history/{contract-name}/`, display quick summary (score, findings, deployment status)
- [X] T019 [US2] Implement `--list` mode in `audit.report.md` - Query all audits for contract from `.audit/history/{contract-name}/`, display table with dates, scores, statuses, findings counts, and report links
- [X] T020 [US2] Implement trend analysis in `--list` mode - Calculate score progression (improving/degrading/stable), identify patterns across audits, generate recommendation based on trend
- [X] T021 [US2] Implement `--compare` mode in `audit.report.md` - Load two specified audit runs, compare findings (fixed, new, unchanged), calculate score delta, assess risk level changes
- [X] T022 [US2] Add audit history management - Limit to 10 most recent audits per contract (configurable), implement cleanup of old audit data, preserve reports directory
- [ ] T023 [US2] Validate audit comparison on GliskNFT.sol - Run audit, modify contract, run second audit, compare results and verify changes are correctly identified

**Checkpoint**: At this point, audit history tracking should be fully functional - developers can track security improvements over time

---

## Phase 5: User Story 3 - Audit Report Generation and Documentation (Priority: P3)

**Goal**: Generate professional audit documentation with comprehensive structure, code references with line numbers, and multiple export formats suitable for stakeholders

**Independent Test**: Run audit and verify generated report includes all sections (Executive Summary, Detailed Findings with code references and line numbers, Security Score Breakdown, Deployment Readiness Checklist, Tools Used, References)

### Implementation for User Story 3

- [X] T024 [US3] Enhance report template in audit generation - Add industry-standard structure sections: Executive Summary, Methodology, Scope & Limitations, Detailed Findings by Severity, Risk Assessment, Recommendations, References
- [X] T025 [US3] Implement code reference formatting - Extract code snippets from contract source, add file paths and line numbers to all findings, format code blocks with syntax highlighting markers
- [X] T026 [US3] Add educational references to report - Include links to OWASP Smart Contract Top 10, ConsenSys Best Practices, OpenZeppelin Security Guidelines, Trail of Bits resources, SWC Registry for each vulnerability type
- [X] T027 [US3] Enhance beginner-friendly explanations - Add "What This Means" section for each finding, include "Why This Matters" with real-world exploit examples, provide "How to Fix" with code examples, add "Learn More" links
- [X] T028 [US3] Add audit methodology section - Document tools used with versions, explain analysis approach (INoT multi-perspective), describe confidence scoring system, list false positive detection patterns
- [X] T029 [US3] Create professional report formatting - Add markdown tables for findings summary, include visual indicators (✅ ⚠️ ❌), format security score breakdown table, add collapsible sections for readability
- [ ] T030 [US3] Validate report quality on GliskNFT.sol - Verify all code references include line numbers, check all findings have beginner explanations, confirm industry references are present, validate report is stakeholder-ready

**Checkpoint**: All user stories should now be independently functional - professional audit reports suitable for investors and third-party audit preparation

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [X] T031 [P] Update `CLAUDE.md` with audit command documentation (usage examples, configuration options, best practices)
- [X] T032 [P] Add example audit configuration file to documentation with common patterns and thresholds
- [ ] T033 Test all quickstart.md scenarios - Scenario 1: First-time audit on GliskNFT.sol, Scenario 2: Second audit after code changes, Scenario 3: View audit history
- [ ] T034 Validate all success criteria from spec.md: SC-001 (3-5min execution), SC-002 (95%+ pattern accuracy), SC-003 (<10% false positives), SC-004 (100% code references), SC-005 (2min comprehension), SC-007 (trend comparison), SC-008 (95% autonomous)
- [X] T035 [P] Add troubleshooting guide for common issues (tool installation, compilation errors, timeouts, false positives)
- [ ] T036 Perform end-to-end validation - Run complete audit workflow on GliskNFT.sol, verify all phases complete successfully, check report accuracy and usefulness, validate deployment readiness decision

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T003) - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion (T004-T006)
  - User Story 1 (P1): Core audit functionality - no dependencies on other stories
  - User Story 2 (P2): Audit history - depends on US1 producing audit data, but is independently testable
  - User Story 3 (P3): Enhanced reporting - depends on US1 report structure, enhances report quality
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - T007-T017 must be executed sequentially (building audit.md command phases)
  - Core MVP - all other stories build on this
- **User Story 2 (P2)**: Can start after US1 T013 (audit history creation) - Independently testable
  - T018-T023 can proceed once audit data structure exists
  - Adds value without modifying US1 functionality
- **User Story 3 (P3)**: Can start after US1 T014 (report generation) - Independently testable
  - T024-T030 enhance report format without breaking existing functionality
  - Can be implemented and tested independently

### Within Each User Story

- **User Story 1**: Sequential execution required (T007→T017) as each task builds the audit.md command phases
- **User Story 2**: Sequential execution recommended (T018→T023) as each task adds to audit.report.md functionality
- **User Story 3**: Sequential execution recommended (T024→T030) as each task enhances the report template

### Parallel Opportunities

- **Phase 1 (Setup)**: All tasks marked [P] can run in parallel (T001, T002, T003)
- **Phase 2 (Foundational)**: T004, T005, T006 should be sequential (dependencies on each other)
- **Phase 6 (Polish)**: Tasks marked [P] can run in parallel (T031, T032, T035)
- **Across User Stories**: Once US1 core is complete, US2 and US3 can proceed in parallel by different developers

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all setup tasks together:
Task: "Create `.audit/` directory structure"
Task: "Create `.audit/config.json` with default configuration"
Task: "Update `.gitignore` to exclude `.audit/` directory"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003) - ~5 minutes
2. Complete Phase 2: Foundational (T004-T006) - ~30 minutes
3. Complete Phase 3: User Story 1 (T007-T017) - ~2-3 hours
4. **STOP and VALIDATE**: Test comprehensive audit on GliskNFT.sol
5. Verify deployment readiness decision is accurate and useful

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (T007-T017) → Test on GliskNFT.sol → MVP complete! 🎯
3. Add User Story 2 (T018-T023) → Test history tracking → Enhanced tracking
4. Add User Story 3 (T024-T030) → Test report quality → Professional reports
5. Complete Polish (T031-T036) → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (~30-40 minutes)
2. Once Foundational is done:
   - Developer A: User Story 1 (core audit) - ~2-3 hours
3. Once US1 core complete:
   - Developer A: User Story 2 (history tracking) - ~1 hour
   - Developer B: User Story 3 (enhanced reporting) - ~1.5 hours
4. Team completes Polish together (~30 minutes)

**Total estimated effort**: 3-4 hours focused implementation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 1 is the MVP - delivers core audit functionality
- User Story 2 adds historical tracking without modifying US1
- User Story 3 enhances report quality without modifying US1/US2
- Tests are NOT included (not explicitly requested in spec)
- Commit after completing each phase
- Stop at any checkpoint to validate story independently
- Avoid: modifying contracts/ directory (audit targets only), adding tests unless requested, creating unnecessary abstractions

---

## Success Criteria Mapping

Each user story maps to success criteria from spec.md:

**User Story 1 (Pre-deployment Validation)**:
- SC-001: Comprehensive audit 3-5min for 500-1500 LOC (T017)
- SC-002: 95%+ pattern accuracy (T004, T010, T011)
- SC-003: <10% false positive rate (T004, T010)
- SC-004: 100% findings have code references (T014)
- SC-005: Beginner comprehension in 2 minutes (T011, T014)
- SC-008: 95% autonomous operation (T016)

**User Story 2 (History and Comparison)**:
- SC-007: Audit history enables trend comparison (T019, T020, T021)

**User Story 3 (Report Generation)**:
- SC-004: 100% findings have code references with line numbers (T025)
- SC-005: Clear deployment readiness for beginners (T024, T027)

All success criteria validated in Phase 6 (T034).
