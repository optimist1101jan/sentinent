# SDE-I Phased Action Plan

> Testing is ~15% of an SDE-I's job. This plan shows where it fits in the bigger picture.
> **60% of testing roadmap (Layer 1 done) = green light to move forward.**

---

## SDE-I Day-to-Day Breakdown

```
├── 50%  Writing features / fixing bugs
├── 15%  Writing tests for what you built
├── 10%  Code reviews
├── 10%  CI/CD, deployment, monitoring
├── 10%  Debugging production issues
└──  5%  Documentation
```

You write tests **for your own code**, not as your main job.

---

## What "60% Testing Done" Means

```
Testing Roadmap (31 tests total)
├── Layer 1 — Core:     15 tests  ← DO ALL (non-negotiable)
├── Layer 2 — Context:   7 tests  ← Do 4-5
├── Layer 3 — Pipeline:  6 tests  ← Do 2-3
└── Layer 4 — E2E:       3 tests  ← Skip for now
──────────────────────────────────
60% ≈ 19 tests = Layer 1 complete + half of Layer 2
```

**Layer 1 complete = foundation is solid. Move on.**

---

## Phased Execution Order

### Phase 1 — "Stop Being Amateur"

> Do these together. This is ground zero.

- [ ] Understand testing concepts (reading strategy docs)
- [ ] Write Layer 1 tests (~15 tests)
- [ ] Fix secrets (`API_KEY.txt` → environment variables) — 30 min
- [ ] Structured logging (`print()` → `logging` module) — 1 hr

**⬇ MOVE ON after this ⬇**

### Phase 2 — "Look Professional"

> Automation + code quality. This is what shows up on your GitHub.

- [ ] GitHub Actions CI/CD (auto-runs tests on every push)
- [ ] Type hints + docstrings on all public methods
- [ ] `ruff` linting + `pyproject.toml`
- [ ] Dockerfile + docker-compose

**⬇ MOVE ON after this ⬇**

### Phase 3 — "Impress in Interviews"

> Architecture upgrades + documentation that shows design thinking.

- [ ] REST API layer (Flask endpoints)
- [ ] SOLID refactoring (abstract `LLMProvider` interface)
- [ ] `DESIGN_DECISIONS.md` (explain WHY you cache, WHY 5-turn cycles)
- [ ] Fill remaining tests (Layer 2-3)

---

## Key Insight

You don't "finish" testing before moving to CI/CD or Docker.
In fact, **CI/CD right after Layer 1 tests** is the smart move —
your tests run automatically, and your GitHub shows green badges.

```
Layer 1 tests → secrets fix → logging → GitHub Actions
     ↑ This is your Phase 1. Everything else builds on top.
```
