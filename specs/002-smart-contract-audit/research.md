# Research: Smart Contract Audit Process Framework

**Date**: 2025-10-13
**Feature**: 002-smart-contract-audit
**Purpose**: Research context management approaches and Introspection of Thought methodology

## Research Areas

### 1. Context Management Approaches

**Research Question**: How can we handle large audit outputs and security analysis within Claude Code's context limits?

#### .context Repository Analysis

**Source**: https://github.com/forefy/.context

**Key Findings**:

1. **Structured YAML Prompts**: Uses YAML-based instruction files to efficiently guide AI agents with domain-specific tasks
   - `agents/`: Agent-specific instruction sets
   - `prompts/`: Targeted, context-aware task instructions with `expected_inputs` and `expected_actions`
   - `outputs/`: Numbered audit runs with standardized report formats

2. **Modular Architecture**: Breaks large tasks into focused modules
   - `knowledgebases/`: Vulnerability pattern collections loaded selectively
   - Predefined templates minimize repetitive context
   - Clear separation between instructions, data, and outputs

3. **Output Standardization**: Generates comprehensive audit trails with consistent formats
   - Numbered run directories (e.g., `outputs/001-solidity-audit/`)
   - Standard file naming (findings, recommendations, summary)
   - Enables historical comparison without re-reading all past audits

**Applicability to Our Framework**:
- ✅ **Adopt**: Structured output directories (`.audit/history/`, `.audit/reports/`)
- ✅ **Adopt**: Standard report formats for consistent parsing
- ❌ **Skip**: YAML prompts (we'll use .claude markdown commands which are more idiomatic)
- ✅ **Adapt**: Modular knowledge bases → false positive patterns library

#### Alternative: Spec-Kit Pattern

**Current Usage**: Spec-kit uses structured plan files with phases/tasks

**Advantages**:
- Already familiar to GLISK development workflow
- Integrates with existing `/speckit.*` commands
- Single-agent sequential execution (cost-efficient)
- Clear phase boundaries prevent context bleed

**Application to Audit**:
- Phase 0: Prerequisites check + tool installation
- Phase 1: Run security tools + collect outputs
- Phase 2: Analyze findings + apply false positive patterns
- Phase 3: Generate report + calculate security score

**Decision**: **Use spec-kit pattern as primary approach**

**Rationale**:
1. Cost-efficient (avoids agent delegation)
2. Familiar workflow (reuses existing patterns)
3. Clear phase separation (manage context per phase)
4. File-based state (can resume if context exceeded)

#### Hybrid Approach for Context Management

**Strategy**:

1. **Structured Plan Files** (spec-kit pattern):
   - `audit-plan.md`: Defines phases for audit execution
   - `audit-findings.md`: Stores raw tool outputs (phase 1)
   - `audit-analysis.md`: Stores categorized findings (phase 2)
   - `audit-report.md`: Final beginner-friendly report (phase 3)

2. **Incremental Processing**:
   - Process findings in batches (e.g., 10 at a time)
   - Write intermediate results to files after each batch
   - Next phase reads only summary, not raw data

3. **Smart Summarization**:
   - Raw Slither output: 100-500 lines → Summarize to 20-50 lines of critical findings
   - False positive filtering: Reduce noise before main analysis
   - Only escalate actionable findings to final report

**Constraint Handling**:
- If contract exceeds 1500 lines: Error with guidance to split or use professional audit
- If tool output exceeds 3000 lines: Auto-summarize by severity (Critical→High→Medium→Low→Info)
- If context near limit: Save progress, suggest continuing with `/audit.continue`

---

### 2. Introspection of Thought (INoT) Methodology

**Research Question**: How can we improve AI reasoning quality for accurate security finding interpretation?

#### Method Overview

**Source**: arXiv 2507.08664 - "Introspection of Thought Helps AI Agents"

**Core Concept**:
INoT is a framework that creates internal multi-agent debate within a single LLM call, enabling self-denial and reflection without external iterations.

**Key Innovations**:

1. **LLM-Read Code in Prompt**: Defines reasoning logic as code-like structures in the prompt
   - Explicit reasoning steps embedded in prompt
   - Self-correction happens within single inference
   - Reduces token cost by 58.3% vs traditional iterative approaches

2. **Virtual Multi-Agent Debate**:
   - Simulates multiple perspectives within one model call
   - Agent A: Presents finding
   - Agent B: Challenges severity/applicability
   - Agent C: Synthesizes final assessment
   - All happens in structured prompt, not separate API calls

3. **Performance**:
   - Average 7.95% improvement across benchmarks
   - Lower token cost than baseline methods
   - Particularly effective for reasoning-heavy tasks

#### Related Techniques

**Chain of Thought (CoT)**:
- Breaks reasoning into explicit intermediate steps
- "Think step-by-step" prompting
- Good for: Showing reasoning process to user

**Self-Reflection**:
- AI evaluates its own outputs for quality
- Recognizes limitations and errors
- Good for: Identifying when confidence is low

**RISE (Recursive IntroSpEction)**:
- Fine-tuning approach for introspection capability
- Learns from previous unsuccessful attempts
- Good for: Long-term improvement (not applicable to our use case)

#### Application to Security Finding Interpretation

**Problem Statement**:
AI agents tend to either:
- **Exaggerate**: Flag every Slither warning as critical
- **Downplay**: Dismiss real vulnerabilities as "acceptable pattern"

**INoT-Inspired Solution**:

```markdown
# Finding Interpretation Prompt Structure

## Raw Finding
[Slither output: "Reentrancy in function X"]

## Internal Debate (within single prompt)

### Perspective 1: Security Concern
- What vulnerability class is this?
- What's the worst-case exploit scenario?
- Has this pattern caused real exploits? (reference knowledge)

### Perspective 2: Context Analysis
- Is reentrancy protection present? (check modifiers)
- What's the actual state change order? (analyze code)
- Is this OpenZeppelin library code? (check source)

### Perspective 3: Beginner Translation
- If Critical: "This MUST be fixed - here's how..."
- If Medium: "Consider this tradeoff - here's why..."
- If False Positive: "Safe because X, Y, Z patterns present"

## Final Assessment
[Synthesized judgment with confidence level]
```

**Structured Decision Tree**:

```
For each finding:
1. Classify vulnerability type (reentrancy, access control, etc.)
2. Check for protective patterns (nonReentrant, onlyOwner, etc.)
3. Assess exploitability (state changes before/after external call)
4. Cross-reference with known-good patterns (OpenZeppelin, etc.)
5. Calculate confidence score (high/medium/low)
6. Generate beginner-friendly explanation based on confidence

If confidence < 70%: Flag as "NEEDS EXPERT REVIEW"
If confidence >= 70%: Provide clear action (fix/accept/ignore)
```

**Implementation Plan**:

1. **Phase 2 Analysis Prompt** includes INoT structure:
   - Define 3 virtual agents (Security, Context, Translation)
   - Each agent outputs structured assessment
   - Synthesize into final judgment

2. **False Positive Detection** uses multi-perspective:
   - Pattern matching (Agent 1): "Does code match safe pattern?"
   - Code flow analysis (Agent 2): "Is state change order safe?"
   - Library source check (Agent 3): "Is this trusted library code?"

3. **Confidence Scoring**:
   - High confidence (90%+): All 3 agents agree
   - Medium confidence (70-90%): 2 of 3 agents agree
   - Low confidence (<70%): Disagreement → escalate to human

**Benefits for Beginner Users**:
- Avoids "just review this" non-answers
- Provides clear reasoning for each judgment
- Shows confidence level (transparency)
- Offers specific actions (not vague warnings)

---

## Recommendations

### Context Management
**Decision**: Adopt hybrid spec-kit + structured outputs approach

**Justification**:
1. **Cost-efficient**: Single-agent sequential processing, no delegation
2. **Familiar**: Reuses existing GLISK workflow patterns
3. **Scalable**: Handles 500-1500 line contracts within context limits
4. **Resumable**: File-based state allows continuing if interrupted

**Implementation**:
- Create `audit-plan.md` with phases (prerequisites, scan, analyze, report)
- Store intermediate results in `.audit/` directory
- Use incremental processing (batch findings, summarize outputs)

### Introspection of Thought
**Decision**: Integrate INoT-inspired multi-perspective analysis into Phase 2 (finding interpretation)

**Justification**:
1. **Accuracy**: Multi-agent debate reduces exaggeration/downplaying
2. **Efficiency**: Happens in single prompt, not separate API calls
3. **Transparency**: Shows reasoning process to beginner users
4. **Confidence**: Provides score to indicate when expert review needed

**Implementation**:
- Design Phase 2 prompts with 3 virtual agents (Security, Context, Translation)
- Structured decision tree for finding assessment
- Confidence scoring (high/medium/low) based on agent agreement
- Beginner-friendly explanations generated by Translation agent

---

## Research Artifacts

**Papers Referenced**:
- [2507.08664] Introspection of Thought Helps AI Agents (arXiv, 2025)

**Repositories Analyzed**:
- https://github.com/forefy/.context (Context management patterns)

**Techniques Evaluated**:
- Chain of Thought (CoT): ✅ Use for showing reasoning to user
- Self-Reflection: ✅ Use for confidence scoring
- RISE: ❌ Skip (requires fine-tuning, not applicable)
- Agent Delegation: ❌ Skip (cost-inefficient per user requirement)
- YAML Prompts (.context): ⚠️ Adapt (use .claude markdown commands instead)
- Structured Outputs (.context): ✅ Adopt (standard report formats)

---

## Phase 1 Prerequisites

Based on research, Phase 1 design requires:

1. **Audit Plan Template**: Define 4 phases (prerequisites, scan, analyze, report)
2. **Finding Schema**: Standardized JSON format for tool outputs
3. **False Positive Patterns Library**: OpenZeppelin + common safe patterns
4. **INoT Prompt Templates**: Multi-perspective analysis prompts for Phase 2
5. **Report Template**: Beginner-friendly markdown format with confidence scores

All prerequisites identified. Ready for Phase 1: Design.
