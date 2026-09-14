# Learning review — 2026-09-14

## Outcome

Promoted recurring process lessons into root best practices: preserve disproofs, distinguish implementation milestones from objective improvement, align player/observer evidence, protect the real objective, and keep experiment retrieval current. Existing matching, identity and human-direction practices gained additional evidence. No game strategy, dated API command or historical submission permission was promoted.

## Coverage

Refreshed local agent-transcripts database: **2,942 sessions / 1,814,143 messages** across Claude, Codex, OpenCode and Auggie. Scoped inventories cover 833 sessions; global FTS found 1,102 additional matches. The 1,935 discovered sessions include helpers, injected-document hits and adjacent work. Inventories distinguish those from candidates and substantive reads. This is a global search with selected detailed review, **not an exhaustive semantic reading of every message**. Unreviewed candidates supply no promotion evidence.

Evidence is historical transcript evidence, not a rerun of old experiments. Null parent metadata alone does not prove independence. Summaries below cite exact `source:session_id@seq`; use the agent-transcripts project to retrieve surrounding turns.

## Disposition

- Promote the supported recurring principles described above, at process scope.
- Retain game mechanics/tuning and single incidents as scoped/tentative.
- Preserve negative outcomes and superseded instructions; July's removal of the pre-upload smoke gate supersedes June's earlier allowance.
- Treat evaluator visibility bugs as potential attribution errors, not automatic invalidation of every observation.

## Evidence reviews

# Player lab transcript breadth pass (2026-09-14)

## Scope and limits

Read session-search skill and transcript DB AGENTS. Parent refreshed DB. Read-only SQLite; initial FTS search used repo JBoggsy/player_labs, widened to all cwd containing personal_labs/player_labs because old/deleted worktrees are missing repository attribution.

244 sessions since June 1: 125 Claude, 95 Codex, 24 Auggie. Complete metadata/first-prompt inventory: learning-evidence-2026-09-14/recent-sessions.json. Dispositions: 157 candidate optimization/setup/adjacent sessions (prompt-level reviewed, not a claim of full transcript review); 36 approval-review transcript copies excluded; 24 retrieval/helper sessions not independent lesson evidence; 19 no usable direct prompt under conservative parser; 8 known linked delegated sessions not independent. Only selected substantive actual user and assistant turns were read closely. This pass is not exhaustive deep reading of all candidate sessions. Repeated copied prompts, synthetic AGENTS/skill injections, cross-session messages and stop-hook reminders were excluded as independent evidence. Approval-review sessions can contain seemingly genuine assistant outcomes; do not count those.

## Strong promotion candidates: repeated independent evidence

1. **Separate observed mechanism from outcome correlation.** Reject tautologies such as winners living less time because they end games faster; generate competing causal explanations and discriminating event-level tests. User corrections: claude-code:98860ca8-5934-4c30-bff0-03e2776c21a7@13 (July 14 reporter trivial correlations); claude-code:18861288-8a4a-4897-b018-380dd2de6619@13 (July 21 CTF, kills can mean aggression OR accuracy; captures can mean several mechanisms); claude-code:b32116fd-190a-4356-bfd5-e995ce6f391f@13 (July 28 excludes trivial correlations, demands mechanistic experiments). These are distinct root sessions, not repeated docs.

2. **Join the player's beliefs and decisions to objective events.** Explain what was observed/believed, what was chosen, what was actuated, and what actually happened; add tracing only when the required diagnosis is not already observable. User: claude-code:f70c9801-7ee7-499b-97f9-4fd0848a6b8e@371 and @407 (June 10 lightweight latency instrumentation and perception versus actual replay); claude-code:a1d94ede-9fb0-462f-8800-0f619670c16a@5874 (July 6 Cady beliefs/decisions/mode/social trace); claude-code:b32116fd-190a-4356-bfd5-e995ce6f391f@13 (July 28 synchronized truth/belief event log). Diagnostic principle is cross-game; exact trace formats remain game-specific.

3. **A controlled comparison and a live-field survey answer different questions.** Fresh baseline/candidate against matched opponents isolates change; tournament-style surveys randomize the remaining field and natural roles. User: claude-code:63658f66-83c7-482e-a805-d58527e10975@4132 (June 8 changing competitors means measure improvement now); claude-code:b6c3f0b3-7275-4b74-bfac-1dad74ab3f1f@377 (June 30 asks fixed per-opponent sets across arms); claude-code:9ba09582-d86d-4b7d-8b42-62a24349a8f9@1754/@2850 (July 6 correction of seven-player fixed field to random champions/roles). Preserve intent, do not infer current API flags from these old records.

4. **Refutations and inconclusive results survive; implementation success is not gameplay improvement.** Actual outcomes: claude-code:3b8b578b-3226-4a33-945a-5aa70bcba177@1441 (July 21 premise refuted, docs-only closeout), @1464 (two levers refuted, code reverted, docs/version log retained); codex:019fd42f-c474-76d2-a8c1-780db07ca672@2568 (August 6 protocol safety fixed but liveness architecture refuted; v52 checkpoint not accepted gameplay improvement); codex:01a0204d-c438-7ef0-b802-f47eae01a053@5734 (August 21 small 2-2 outcome inconclusive; reject if signaling changes without economy gain). No parent edges for these selected sessions. These are assistant outcome reports, not independently rerun measurements; use them for process lessons, not current quantitative claims.

5. **Keep concise working state separate from noisy candidate lessons, with repeat-evidence promotion.** Direct user design: claude-code:f70c9801-7ee7-499b-97f9-4fd0848a6b8e@158 (June 10); independent followup claude-code:0e7b14ca-ffd5-4137-9456-47485d3c6f87@1644 (June 11 wants per-session rotation/archive and periodic promotion because instructions alone are not reliable). Avoid promoting duplicate archive copies or hooks as independent confirmations.

6. **Help the human choose strategy from clear evidence, then honor task-specific autonomous scope.** User: claude-code:3c867a71-3057-4e87-a149-4185e82ee728@142 (June 8 big strategic jumps remain human-led); claude-code:63658f66-83c7-482e-a805-d58527e10975@5225 (ask direction after replay + hypotheses); claude-code:0c53c564-d48c-4e57-b020-f489554ef6b2@7 (June 9 reject technical setup narration as newcomer UX); claude-code:9d12b0f9-7158-4259-9eb3-c153921f0c3e@2930 (June 27 clear visual experiment design). Later exceptions: claude-code:3b8b578b-3226-4a33-945a-5aa70bcba177@1013/@1514 and claude-code:b32116fd-190a-4356-bfd5-e995ce6f391f@616 explicitly authorize autonomous loops/submissions. Do not generalize temporary authorization into a durable submit-at-will rule.

## Superseded or contextual practices

- June 8 allowed a local smoke gate (claude-code:63658f66-83c7-482e-a805-d58527e10975@1975); July 2 explicitly removes smoke/gate-1 due slow iterations (claude-code:a6c575cd-c239-4909-9d44-4026c52aef12@10). Historical smoke instruction must not be revived as repeated best practice.
- June 27 experiment design must be shown clearly to user (claude-code:9d12b0f9-7158-4259-9eb3-c153921f0c3e@2930), but later explicit loop authorization exists. Preserve reviewable design and current scope; do not invent per-query reapproval when already authorized.
- Game-specific heuristics are not general lessons: July squad strategies were explicitly rolled back by July 23 user due game behavior (claude-code:486b62d8-dd4b-4d96-8b50-bde11de7ed1e@2453; matching copy in 991d1017... is not independent). August 29 removes outdated threat-axis abstraction (claude-code:029a80f3-7b79-45a8-9004-3a9bcefbcf24@17). Retain version/epoch scope and refutation rather than globally promoting strategy.
- Exact local SDK versions, API paths, timeout constants and game physics claims were intentionally not promoted. A quantized actuator contract was learned in a WoW-specific experiment (codex:019fe273-272a-71e3-b2ee-3bedeacfdd0a@6578), useful evidence to verify engine contracts but not a universal action rule.

## Deferred deeper audit

To claim all policy-improvement sessions have been deeply assessed, follow the 157 candidate rows and unresolved 19, widen beyond cwd to FTS player/lab aliases in sibling game repositories, and disposition all related branches/children against later outcomes. Parent is covering cross-repo histories. This report provides only supported repeated lessons and explicit audit limits.


# Earlier policy work: conservative transcript findings

## Coverage and limits

Metadata inventory: 589 sessions across personal_cogs (386), players/bitworld player paths (104), agent-policies (46), optimizer seed-lab (53). See learning-evidence-2026-09-14/early-sessions.md for every source:id@seq. Broad FTS union (policy/player/agent/optimization/experiment/replay/perception/navigation/whisper/tournament/leaderboard) matched 543 of these; these are discovery candidates, not 543 reviewed optimization sessions. Scope may omit relevant work conducted from unrelated directories. Read-only DB after parent refresh; no transcript refresh or DB writes performed by this worker.

Substantive selected reads: ten sessions (two detailed movement/fallback investigations; three Persephone investigations; Among Them results/tracing and disconnect investigations; original setup; frame-recording/viewer session; optimizer evidence-audit session). Ratings were used only to find candidates; apparent rater hallucination judgments based on absent visible tool outputs were NOT adopted. Assistant hypotheses below are historical claims, not verified current mechanics. Tool-result user rows, injected instruction/user-context blocks, compaction summaries, and tool calls were not treated as independent user evidence. No linked parent-child edges among the promotion's primary sessions were found; distinct run narratives and direct user corrections support independent recurrence.

## Recommended small promotion: investigation ledger

When an investigation starts repeating theories, maintain a short ledger: observed symptom; candidate mechanism; separating check; result; ruled out/still open; next check. Preserve negative findings so the next turn/session does not restart a disproven line. Reconcile the ledger before another fix. This is an operational complement to existing falsifying-query discipline, not a new approval gate.

Evidence, two independent sessions:
- opencode:ses_21eb30b06ffeL6353Ov27zhdA1@413 — James directly asks for theories, attempted diagnoses, results, concretely disproven theories, promising survivors, and tests after circular debugging. @415 contains the resulting ledger. @508 says the first fix did not solve the movement symptom; @600 reports the later task-commitment fix reduced captured-replay goal runs from 23 to 5. Limit: replay behavioral evidence, no demonstrated live competitive improvement.
- opencode:ses_21af0e707ffeWhoJeouK9agHhn@145 — James again asks to collate thinking and identify disproven theories. @545 explicitly requests plausible hypotheses plus temporary measurement. @586 reports timing that overturns the repeatedly asserted localization-spiral explanation: interstitial OCR cost was 22ms/frame while gameplay was faster. Limit: local functionality/performance result, not tournament improvement.

## Supported refinement: evidence should support both human and agent inspection

Store captured observations with the decoded perception and tick keys; make a useful viewer and a machine-readable inspection path. This is mostly already covered by observability doctrine; promote only the missing concrete storage/discovery habit, if any.
- opencode:ses_1ffe75d89ffeHvW4p2ARluHh51@98 — James asks for a CLI-invoked saved-frame viewer. @182 requests a palette-character textual representation for agent inspection; @571 asks whether perception.jsonl is stored alongside frames. @518 shows capture must be verified rather than assumed.
- claude-code:ee5aaed4-70d2-4597-b012-9d348f4f1e2b@297 — James defines the goal as postmortem, recorded-frame overlays, and automated evaluation, explicitly saying seen frames should be recorded. @432 asks to exclude high-noise changing fields from change detection; @441 reports elapsed ticks removed from change events but retained in periodic snapshots.
Counterweight: do not generalize one requested PICO-8 textual viewer or one logging interval into a universal tool requirement.

## Duplicate principles / useful historical evidence, not new doctrine

### Milestone success is not objective success
- claude-code:3b14ac5a-1d66-4524-94c0-59a48466d223@1562 claimed whisper lifecycle pieces worked end-to-end but still described solo whispers and missing interactions.
- claude-code:aae25940-ade3-41bc-b817-517dc86ccebf@458, a later independent evaluation, reported 0/5 wins and no exchanges. @898 reports first server-confirmed joins in 4/6 games but 0 wins; @1272 and @1938 still report no completed role exchanges. These are partial capability milestones, not player promotion evidence.
Existing doctrine already says capability-used, trace-confirmed, objective-linked metrics. Reuse as supporting examples, avoid another rule.

### Do not diagnose server lifecycle from client-local endpoints
- claude-code:5f9e8287-da92-4dff-bf39-2511bcaf0700@186 — user corrects impossible early-imposter-death explanation.
- @533 retracts teleport hypothesis; @588 invents plausible AFK-kick mechanism without server evidence; @762 reasons about short game end from client traces; @770 James asks to verify server logs distinguish actual game end from all clients disconnecting.
- @633 admits local fixture ended before targeted failure window.
Single rich session here; keep as tentative case study or support existing authoritative-ground-truth/local-vs-hosted practices. Do not retain asserted AFK kick as fact.

### Identity joins must be verified
- claude-code:e5e23b1b-d4da-478d-b010-bb374c477eec@630 codifies actual per-policy slot lookup rather than assignments-array positions.
- claude-code:3b14ac5a-1d66-4524-94c0-59a48466d223@472-479 reverses diagnosis after realizing baseline players, not Eurydice, generated observed whisper events.
Already covered by authoritative per-policy joins. Do not retain historical ghost-slot explanation at e5e23...@599 as confirmed mechanism.

### Use canonical runner, not a parallel reimplementation
- opencode:ses_21eb30b06ffeL6353Ov27zhdA1@417 is explicit James correction to use bitworld_runner.
Single direct policy-session observation; already general reuse-before-build guidance.

### Independent provenance matters more than detailed prose
- claude-code:deb66092-1c6c-4f84-8714-d56de5c245c3@2139: optimizer audit found a positive control with real batches, while two other runs had no batches under their identity and one had 11 recorded IDs all returning 404 despite detailed statistical reports. Agent explicitly leaves deletion/scope/failure/fabrication cause unresolved and downgrades conclusions.
Tentative single-session audit; do not claim fabrication proven. Supports existing provenance/positive-control discipline. Strong warning against trusting highly formatted reports as evidence.

## Inventory disposition

- The above references: substantively read, conservative findings recorded.
- Other rows: discovery-only candidates, no promotion. Empty sessions, setup, subagents, SDK/ops maintenance and injected-doc matches remain possible.
- No strategy constants, opponent identities, dated API commands, source-version assumptions, secret material, or raw transcript excerpts should migrate into durable general doctrine.


# Global policy transcript discovery supplement

Searched full refreshed DB with three broad FTS unions: policy/player/agent plus optimization/experimentation/strategy/evaluation terms; known lab/game names; experience request/A-B/optimizer terms. Removed the 833 prior session IDs (244 recent+589 early; disjoint). Result:1102 additional session matches. Raw-message-shape screening left 460 sessions with 707 candidate text turns; the rest were injected/tool/copy-only hits under a conservative parser. No claim every remaining message is human-authored or every candidate is policy work. Complete sanitized disposition inventory: `learning-evidence-2026-09-14/global-sessions.json`.

- 642: excluded: FTS hits only injected/tool/copy content under conservative parser
- 89: review/retrieval/helper candidate: no independent lesson promoted
- 265: adjacent or keyword false-positive: not promoted to policy-improvement evidence
- 80: optimization-related prompt candidate: substantive follow-up needed except cited evidence
- 5: linked child: candidate evidence only, not independent
- 21: retrieval/helper: not independent human correction

## Substantive evidence read and new/promotable lessons

### Optimize the actual target, not its proxy; do not alter the measuring environment to manufacture improvement

- Actual human instruction `claude-code:490a2b5b-73c1-4bec-9551-35b387773983@2791` (July 15 optimizer-seed meta-optimizer): broad persona satisfaction is a proxy for helping real human newcomers; do not p-hack/reward-hack to satisfy the personas. Surrounding assistant response @2794 says preserve persona/scenario/rubric during a campaign, report all runs, and make one attributable change. The assistant response is proposed process, not proof all runs met it.
- Independent actual human instruction `claude-code:5124496e-3ee5-4bbe-b738-999a718ff370@1006` (September 1 starter policy optimization in coworld-ctf): run an 8.5-hour improvement loop, measure relevant behavior; investigate both policy and game when blocked, but do not change game rules to advantage policy. Crashes, disconnects, upload and latency bugs may be fixed within granted scope.
- These are separate root sessions with no known parent edges. Promote the principle, not temporary autonomous submission authorization or fixed 8.5-hour duration.

### Validate evaluator visibility before attributing an observed failure to the player/optimizer

- Actual user `claude-code:83a9f827-79cb-41ae-86ee-3b77bbb53113@729` noticed a persona conversation began with "Everything above stands" despite having no prior context.
- Actual assistant diagnosis @771: one CLI invocation emitted 7 interleaved text blocks, including 4,918-character recon; harness only delivered its 862-character final result. The persona never saw the walkthrough.
- Actual user @776 asked whether this invalidates findings. Assistant @779 explicitly separates user-experience findings (based on what persona really received) from suspect attribution (agent may have written allegedly missing information in dropped blocks). DO NOT summarize as all findings invalidated.
- This is one concrete incident, so keep this exact lesson as tentative unless paired with independently verified collection/decoder failures from other workers. It supports and illustrates the repeated truth/belief/observer-alignment principle already evidenced in recent-lab report.

### Re-check improvement against historical baselines and deployment-representative conditions

- Actual human `claude-code:425dc11e-1c8d-4d12-bf44-adf01b6fa796@395` (April 30 alpha_cog) requests tournaments against prior versions so adaptation to local meta does not hide regressions. Exact copy appears in `codex:019de5a5-fadf-70b3-8773-2072cabae94c@621`; count these as ONE provenance cluster even absent parent metadata.
- Independent human `claude-code:3d57efa8-dd72-43f4-8a00-809d9728282b@3067` (September 4 CTF navigation): productionEC 2 boxes differ from Mac; establish baseline and optimize onEC 2. @3077 is duplicate, not confirmation. Scope is performance qualification, not a demand to run every gameplay test onEC 2.
- Combined with recent fresh matched comparisons this supports representative evaluation and regression coverage, but does not justify one universal benchmark format.

### Keep experiment retrieval up to date with results

- Actual human `opencode:ses_20b14e3aaffe6TJnfnmV5DdVmT@439` (May 4 alpha_cog) explicitly requests experiment index regeneration after every completed experiment.
- Separate session `opencode:ses_2042c1ff1ffefETImBU5n4D43k@349` (May 6) repeats fully updating experiment docs and index when shipping a policy.
- These are actual text turns rather than injected AGENTS. They support a discoverability requirement; do not force alpha_cog's graph/RAG or notebook schema into player_labs. OpenCode parent lineage coverage is weaker; treat independence as separate sessions, not mathematically proven independent roots.

## Additional ecosystem discovery

Global search surfaced `cogames_playground/alpha_cog`, `optim-compare` and `optim-compare/seeds/optimizer-seed`, game repos including coworld-ctf and coworld-heartleaf, and adjacent Metta platform work. The optimizer-seed session `claude-code:490a2b5b-73c1-4bec-9551-35b387773983@504` describes a reusable seed plus per-game mixins; @1703 describes cold-start persona-based testing of the optimizer itself. These are historical design/intent evidence, not live verification of current repositories.

## Coverage statement suitable for final report

Searched all ingested sessions globally through FTS plus scoped inventories, with raw-message filtering and selected substantive follow-up. This discovers additional candidates outside known lab checkout paths; it is not an exhaustive reading or semantic classification of all 1.8 M messages. Null lineage is not proof of independence, and matching text is deduplicated when discovered. Historical commands, model choices, runtime versions, and game strategy particulars were not promoted as current truth.
