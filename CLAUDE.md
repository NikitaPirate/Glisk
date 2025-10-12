# glisk Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-10

## Active Technologies
- Solidity ^0.8.20 + OpenZeppelin Contracts v5.x (ERC721, AccessControl, ReentrancyGuard, ERC2981) (001-full-smart-contract)

## Project Structure
```
src/
tests/
```

## Commands
# Add commands for Solidity ^0.8.20

## Code Style
Solidity ^0.8.20: Follow standard conventions

## Recent Changes
- 001-full-smart-contract: Added Solidity ^0.8.20 + OpenZeppelin Contracts v5.x (ERC721, AccessControl, ReentrancyGuard, ERC2981)

<!-- MANUAL ADDITIONS START -->

## Dependency & Environment Awareness

When encountering unexpected behavior with dependencies or tools:

**Core Principle**: Distinguish between "I made a mistake" vs "something external is wrong"

### Before Applying Workarounds, Ask:
- Is this behavior expected for this library/tool version?
- Could the environment be misconfigured? (wrong version, not activated, missing prerequisites)
- Am I using outdated knowledge about this library's API?
- Would my fix degrade the solution? (downgrading versions, removing features, disabling checks)

### If Uncertain About Root Cause:
1. **Investigate first** - check versions, environment state, library documentation
2. **If environment issue suspected** - STOP, explain findings, present options (including user actions if needed)
3. **If degrading solution** - present alternatives and let user choose
4. **If my knowledge may be outdated** - check current documentation or inform user

**Examples of "stop and diagnose":**
- Version conflicts → check if environment needs update, don't auto-downgrade
- Tool showing unusual errors → verify environment activation/configuration
- API not working as expected → check if library updated beyond my knowledge
- Installation failures → check system prerequisites before trying workarounds

**Simple mistakes to fix immediately:**
- Forgot an import, config edit, or installation command

<!-- MANUAL ADDITIONS END -->