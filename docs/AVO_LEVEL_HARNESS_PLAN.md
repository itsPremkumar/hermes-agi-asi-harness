# AVO-Level Intelligent Harness — Complete Architecture Plan

> **Goal:** Build a self-evolving, autonomous harness that supervises Hermes AI agent to achieve frontier-level performance on ARC-AGI-3, SWE-bench, GAIA, and other benchmarks — matching or exceeding NVIDIA AVO's 100% ARC-AGI-3 score.

---

## 1. Reference Architectures

### 1.1 NVIDIA AVO (Agentic Variation Operators)
- **Paper:** arXiv 2603.24517
- **Key insight:** The agent IS the variation operator — it decides what to inspect, what to change, what to test, what to commit
- **Score:** 100% RHAE on ARC-AGI-3 public set (183 levels, 25 environments, 6,624 actions)
- **Core mechanisms:**
  - Persistent memory (carries state across context windows)
  - Supervisor (monitors trajectory, redirects when stuck)
  - Grounded feedback (decisions based on actual outcomes, not self-assessment)
  - Long-horizon loop: hypothesis → act → observe → update → continue
  - Text-only modality (64×64 text grid observations)

### 1.2 VISTA (Visual Harness for Reasoning)
- MIT's Claude Opus 5 harness
- Also reached 100% on ARC-AGI-3 public set
- Used 7,542 environment actions (vs AVO's 6,624)
- Key difference: visual + text observations

### 1.3 Tycho (Active Abstraction with Programmatic World Models)
- Built explicit world models of ARC-AGI-3 environments
- Reached 100% on public set
- Key insight: programmatic world-model construction helps

### 1.4 Self-Refinement / Iterative Improvement
- Generate → Evaluate → Revise → Repeat
- Each iteration improves the output
- Multiple revision cycles compound quality

### 1.5 Multi-Agent Debate
- Multiple agents propose solutions
- Cross-critique and converge on best answer
- Reduces individual agent bias

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AVO-LEVEL SUPERVISOR                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Planner │→ │ Researcher│→ │ Dispatcher│→ │   Monitor     │  │
│  │         │  │          │  │          │  │               │  │
│  │ Goal    │  │ Deep Web │  │ Subagent │  │ Progress      │  │
│  │ Decomp  │  │ Search   │  │ Spawn    │  │ Stall Detect  │  │
│  │ Strategy│  │ Context  │  │ Bot Mode │  │ Score Track   │  │
│  └─────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│         ↑                                    │                  │
│         └────────── Feedback Loop ───────────┘                  │
├─────────────────────────────────────────────────────────────────┤
│                    EVOLUTION ENGINE                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Variation    │  │ Evaluation   │  │ Selection            │ │
│  │ Operator     │  │ Gate         │  │ (Best-of-N)          │ │
│  │              │  │              │  │                      │ │
│  │ Mutate code  │  │ Run tests    │  │ Keep top-K           │ │
│  │ Revise plan  │  │ Score output │  │ Discard rest         │ │
│  │ New approach │  │ Verify truth │  │ Iterate again        │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    HERMES NATIVE TOOLS                           │
│  delegate_task │ web_search │ web_extract │ memory │ cron       │
│  bot_mode      │ git        │ GitHub     │ skills │ terminal   │
│  code_edit     │ MCP        │ subagents  │ goals  │ kanban     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Intelligent Planner
**Purpose:** Decompose complex goals into executable sub-goals with dependencies.

```
Input: "Score 100% on ARC-AGI-3"
    ↓
Output:
  1. [P0] Download ARC-AGI-3 toolkit + public set
  2. [P0] Analyze environment structure (64×64 grid, 16 colors)
  3. [P1] Build environment connector adapter
  4. [P1] Implement hypothesis formation module
  5. [P1] Build persistent memory system
  6. [P2] Implement supervisor (stall detection + redirect)
  7. [P2] Build RHAE scorer
  8. [P3] Run evaluation on public set
  9. [P3] Analyze failures → iterate
```

**Features:**
- Dependency graph (what must complete before what)
- Priority scoring (critical path identification)
- Dynamic re-planning when blockers emerge
- Resource estimation (time, compute, tokens)

### 3.2 Deep Research Engine
**Purpose:** Gather comprehensive context before execution.

**Workflow:**
1. **Search** → web_search with multiple query variations
2. **Extract** → web_extract top-N results for deep content
3. **Synthesize** → combine findings, identify contradictions
4. **Store** → persist in memory for future reference

**Research targets:**
- Benchmark rules, scoring, environment details
- State-of-the-art approaches (AVO, VISTA, Tycho papers)
- Known failure modes and edge cases
- Optimal strategies per environment type

### 3.3 Variation Operator (The AVO Core)
**Purpose:** Generate and evolve candidate solutions through multiple iterations.

**This is the heart of the system — the agent IS the variation operator.**

```
Iteration 1: Generate initial solution
    ↓
Evaluate → Score: 0.45
    ↓
Iteration 2: Revise based on feedback
    ↓
Evaluate → Score: 0.62
    ↓
Iteration 3: New hypothesis, different approach
    ↓
Evaluate → Score: 0.78
    ↓
Iteration 4: Refine edge cases
    ↓
Evaluate → Score: 0.91
    ↓
Iteration 5: Final polish
    ↓
Evaluate → Score: 1.00 ✓
```

**Variation strategies:**
- **Mutation:** Modify existing solution (change approach, fix bugs)
- **Crossover:** Combine best parts of multiple solutions
- **Restart:** Fresh approach when current direction stalls
- **Decomposition:** Break hard sub-problems into easier pieces
- **Abstraction:** Build world models of environment dynamics

### 3.4 Evaluation Gate
**Purpose:** Grounded feedback — decisions based on actual outcomes, not self-assessment.

**For each candidate solution:**
1. **Execute** in real environment (not simulation)
2. **Measure** actual score (RHAE, pass rate, etc.)
3. **Compare** against baseline and previous iterations
4. **Diagnose** specific failure points
5. **Generate** actionable feedback for next iteration

**Key principle:** The evaluator NEVER trusts the agent's self-assessment. Always verify externally.

### 3.5 Supervisor (Trajectory Monitor)
**Purpose:** Monitor agent trajectory, detect stagnation, redirect when stuck.

**Stall detection:**
- Repeated identical actions (no exploration)
- Score plateau (no improvement over N steps)
- Hypothesis stagnation (many untested hypotheses)
- Context overflow (losing track of state)

**Intervention strategies:**
- **Nudge:** "Try a different approach. Last 20 actions were identical."
- **Redirect:** "You have 10 untested hypotheses. Start testing them."
- **Reset:** "Progress stalled. Return to last checkpoint."
- **Escalate:** "This sub-goal is blocked. Reassign to different agent."

### 3.6 Persistent Memory System
**Purpose:** Carry state across context windows and sessions.

**Memory types:**
- **Episodic:** What happened (action history, observations)
- **Semantic:** What we know (hypotheses, confirmed facts)
- **Procedural:** How to do things (skills, strategies that worked)
- **Meta:** How we learn (what strategies lead to improvement)

**Memory operations:**
- **Store:** Save important findings with importance weighting
- **Retrieve:** Find relevant memories by keyword/context
- **Consolidate:** Compress long histories into key insights
- **Forget:** Evict low-importance entries when at capacity

### 3.7 Multi-Agent Orchestration
**Purpose:** Parallelize work across specialized agents.

**Agent roles:**
- **Researcher:** Deep web search, paper analysis
- **Coder:** Implementation, debugging, testing
- **Evaluator:** Run benchmarks, verify correctness
- **Writer:** Documentation, reports, summaries
- **Reviewer:** Code review, quality assurance

**Coordination patterns:**
- **Pipeline:** Researcher → Coder → Evaluator → Writer
- **Debate:** Multiple coders propose, evaluator selects best
- **Divide-and-conquer:** Split benchmark into chunks, parallelize
- **Assembly line:** Each agent does one step, passes to next

---

## 4. Evolution Loop (The AVO Cycle)

```
┌─────────────────────────────────────────────────────────────┐
│                    EVOLUTION CYCLE                           │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ OBSERVE  │───→│ REASON   │───→│  PLAN    │             │
│  │          │    │          │    │          │             │
│  │ Grid     │    │ Form     │    │ Choose   │             │
│  │ State    │    │ Hypoth.  │    │ Action   │             │
│  └──────────┘    └──────────┘    └──────────┘             │
│       ↑                                │                    │
│       │                                ↓                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ UPDATE   │←───│ EVALUATE │←───│   ACT    │             │
│  │          │    │          │    │          │             │
│  │ Memory   │    │ Score    │    │ Execute  │             │
│  │ Beliefs  │    │ Outcome  │    │ Action   │             │
│  └──────────┘    └──────────┘    └──────────┘             │
│                                                              │
│  Repeat until: score ≥ threshold OR budget exhausted         │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 Per-Level Execution (ARC-AGI-3)
1. **Observe:** Receive 64×64 text grid
2. **Reason:** Form hypotheses about environment dynamics
3. **Plan:** Choose action based on best hypothesis
4. **Act:** Execute action in environment
5. **Evaluate:** Measure score change, update beliefs
6. **Update:** Store findings in persistent memory
7. **Repeat:** Until level complete or budget exhausted

### 4.2 Per-Problem Execution (SWE-bench)
1. **Observe:** Read issue description + repo structure
2. **Research:** Find relevant code, understand bug
3. **Plan:** Design patch approach
4. **Implement:** Write the patch
5. **Test:** Run test suite, verify fix
6. **Iterate:** If tests fail, diagnose and revise
7. **Submit:** When all tests pass

### 4.3 Per-Question Execution (GAIA)
1. **Observe:** Read question
2. **Research:** Web search for context
3. **Reason:** Step-by-step chain of thought
4. **Verify:** Cross-check with sources
5. **Answer:** Provide final answer
6. **Confidence:** Rate certainty, flag if uncertain

---

## 5. Self-Improvement Mechanisms

### 5.1 Strategy Learning
- Track which strategies lead to improvement
- Prefer strategies that worked in the past
- Abandon strategies that consistently fail
- Discover new strategies through exploration

### 5.2 Prompt Evolution
- Start with base prompts
- Mutate prompts based on performance
- Keep prompt variants that improve scores
- Discard variants that hurt performance

### 5.3 Skill Acquisition
- When a reusable solution is found, save as skill
- Skills accumulate over time
- Future tasks can leverage existing skills
- Skills are versioned and can be updated

### 5.4 Error Analysis
- After each failure, perform root cause analysis
- Categorize errors (logic, knowledge, execution)
- Generate targeted improvements
- Verify improvements actually help

---

## 6. 24/7 Autonomous Operation

### 6.1 Cron-Based Scheduling
```
02:00 — Nightshift: Run benchmark evaluations
04:00 — Analysis: Analyze overnight results
06:00 — Planning: Generate today's goals
08:00 — Execution: Begin main work
12:00 — Review: Mid-day progress check
14:00 — Continue: Address blockers
18:00 — Summary: Daily progress report
20:00 — Research: Deep web research
22:00 — Prep: Prepare for nightshift
```

### 6.2 Bot Mode Integration
- Supervisor runs as persistent bot
- Monitors all active subagents
- Intervenes when stalls detected
- Reports progress to user periodically

### 6.3 Checkpointing
- Save state after every completed sub-goal
- On failure, resume from last checkpoint
- Never lose more than one sub-goal of progress

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Supervisor core (plan → dispatch → monitor → adjust)
- [ ] Persistent memory system
- [ ] Basic evaluation gate
- [ ] Integration with Hermes delegate_task
- [ ] Cron-based scheduling

### Phase 2: Intelligence (Week 3-4)
- [ ] Deep research engine
- [ ] Variation operator (generate → evaluate → revise)
- [ ] Multi-agent orchestration
- [ ] Strategy learning
- [ ] Error analysis

### Phase 3: Evolution (Week 5-6)
- [ ] Self-improvement loop
- [ ] Prompt evolution
- [ ] Skill acquisition
- [ ] Automatic re-planning
- [ ] Checkpointing + recovery

### Phase 4: Optimization (Week 7-8)
- [ ] Performance tuning
- [ ] Parallel execution optimization
- [ ] Memory consolidation
- [ ] Advanced stall detection
- [ ] Cross-benchmark transfer learning

### Phase 5: 24/7 Operation (Week 9+)
- [ ] Full bot mode deployment
- [ ] Nightshift cron jobs
- [ ] Continuous benchmark evaluation
- [ ] Automatic reporting
- [ ] Self-healing on failures

---

## 8. Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| ARC-AGI-3 public set | 100% RHAE | 0% (not run) |
| SWE-bench Verified | >60% | 0% (not run) |
| GAIA Level 3 | >60% | 0% (not run) |
| Self-improvement rate | +5% per iteration | N/A |
| Stall detection accuracy | >90% | N/A |
| Autonomous uptime | >95% | N/A |

---

## 9. Key Principles

1. **Grounded feedback:** Never trust self-assessment. Always verify externally.
2. **Persistent state:** Memory survives context windows and sessions.
3. **Evolution over generation:** Iterate on solutions, don't just generate once.
4. **Supervision over autonomy:** Monitor trajectory, intervene when stuck.
5. **Decomposition over monolith:** Break big goals into small, verifiable sub-goals.
6. **Learning over static:** Strategies improve from experience.
7. **Parallel over sequential:** Exploit delegate_task for concurrent work.
8. **Checkpoint over restart:** Save progress, resume from failures.

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| OAuth token expiration | Auto-refresh via hermes auth |
| Infinite loops | Budget limits, stall detection |
| Memory overflow | Consolidation, eviction policies |
| Wrong self-assessment | Grounded evaluation gate |
| Subagent failures | Retry with different approach |
| Benchmark data unavailability | Use public sets, synthetic tasks |
| Compute costs | Free tier models, batch evaluation |

---

*End of plan. This is a living document — evolve it as we learn what works.*
