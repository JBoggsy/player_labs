# Player lab modernization audit — 2026-09-14

## Result and scope

Unified the optimization workflow, documentation navigation, tool contracts and learning records. Corrected supported analysis integrations without changing player source, live leagues or historical experiment results. User-authorized scope included supported integrations and conservative promotion of recurring lessons.

Start with the [capability map](../capabilities.md), [tool-building guide](../tooling.md) and [learning guide](../learning.md). The [transcript review](learning-review-2026-09-14.md) contains exact evidence and exclusions.

## Findings and disposition

| Finding | Resolution |
| --- | --- |
| Root workflow said evaluations were free, rejected all local mechanism tests, and had conflicting reapproval rules | Updated cost/local-evidence distinctions and existing-authorization behavior; explicit league/community/remote-write permissions remain |
| Shared build skill only described one game/player | Documented container and game-hosted artifacts; moved player-specific runtime recipe to its lab |
| Long working contexts mixed old objectives, permissions and incompatible live-version claims | Preserved all nine complete originals beside concise handoffs; historical state must be re-resolved |
| API docs/routes lagged current service | Updated request schema reference, boolean leaderboard option, exact version resolution and cursor pagination; migrated downloads to episode-request routes |
| Partial downloads could appear complete; exhausted watches could exit successfully | Coverage markers verify advertised accessible files; per-episode decode failures count toward bounded retries; incomplete downloads exit nonzero |
| Dashboard used removed routes, compressed sparse seat positions and assumed one game's roles | Current routes, explicit seat indices, generic descriptive metrics and terminal failure counts |
| Handwritten A/B approximations and overconfident “noise” labels | Existing SciPy Fisher/Welch tests, BY correction, explicit independent-episode contract and inconclusive wording |
| Repeated teammate observations could inflate comparison sample size | Paintbot aggregates per episode; Crewrift rejects repeated subject seats within a role and excludes whole operationally failed episodes from gameplay metrics |
| Paintbot warehouse guessed two teams and derived winner from score totals | Uses explicit teams and win flags; retains four team totals and unknown outcomes; removed guessed Beacon roles |
| Useful tools missing from guides; Heartleaf still described as scaffolding | Capability map, game analysis links, Heartleaf implementation status and WoW survey/decoder links |
| Repeated lesson hook implementations silently committed changes and could lose malformed entries | One shared implementation, thin lab wrappers, no auto-commit, preserve every nonempty buffer, stop if archival fails; Sugarscape gets lifecycle files/hooks |
| General lesson promotion confused copies, hypotheses and outcomes | Global transcript discovery, lineage/copy exclusions, evidence review, recurring process promotions and explicit tentative/refuted findings |
| Miner template implied ready integrations and causal point recovery | Association-only wording and input checks; unsupported provenance-dependent adapters remain explicitly deferred |

## Documentation audit coverage

Inventoried 504 Markdown/HTML documents at the initial post-edit check, including hidden skill docs. The reusable [audit tool](../../tools/audit_docs.py) checks local file targets and separates historical references. Current file-target checks passed. It does not validate heading anchors, remote URLs or every semantic statement automatically.

Semantic review focused on the root workflow/preferences/onboarding, shared skills and executable contracts, game entry points, working contexts, Paintbot result/seating assumptions and learning lifecycle. Historical reports/design discussions remain dated evidence, not automatically current instructions. The final [document inventory](learning-evidence-2026-09-14/document-inventory.json) has no broken local file targets. A final pass repaired 162 historical link occurrences whose files existed but whose paths were relative to their former locations. Seven references to absent historical source files are now explicitly labeled unavailable instead of presented as working links. The [repair ledger](learning-evidence-2026-09-14/historical-link-repairs.json) preserves old/new targets. Only navigation and availability labels changed; experiment observations and dated line references were not rewritten. Original archive bytes remain in the earlier local checkpoint. This is not a claim that every historical command or line citation remains current.

Lesson archive discovery found 129 Markdown files and 113 byte-distinct bodies before any content normalization. Counts are discovery metadata, not independent confirmations. Promotion used the cited substantive transcript findings; archive copies and injected instructions do not add support.

## Transcript coverage and promoted lessons

Refreshed agent-transcripts: 2,942 sessions, 1,814,143 messages, four agent sources. Scoped inventories plus global FTS discovered 1,935 session candidates/matches, including many excluded helper/injected/adjacent records. The evidence review distinguishes discovery, prompt screening and substantive reading. It does **not** claim a complete reading of all messages.

Promoted recurring process principles: keep disproofs in an investigation ledger; separate functionality milestones from gameplay improvement; verify observation/decision/evaluator visibility; protect the actual objective from proxy optimization; distinguish field surveys from controlled comparisons; update experiment retrieval and concise handoffs alongside results. Game strategy, version-specific mechanics and old permissions stayed scoped or tentative.

## Validation and provenance

- Base repo: `bd38453830a884ff954795967a4d4b3e65ad2ab6`, equal to fetched `origin/main` before edits. Work branch: `modernize-lab-workflow`.
- Project toolchain updated through `uv lock --upgrade-package coworld --upgrade-package softmax-cli` and `uv sync --locked`: **coworld 0.1.47**, **softmax-cli 0.26.34**. Player/game SDK pins were not advanced.
- Current public Observatory OpenAPI checked on 2026-09-14; upload CLI help confirms container and `--file` modes. No authenticated live artifact/roster request was used as validation.
- **26 focused regression checks passed** for shared transport/completeness/retries, sparse identity, exact roster resolution, episode-level outcomes, statistics and lesson preservation. These are analysis-tool checks, not pre-upload player gates.
- Paintbot metadata normalization read **536 stored result pairs** without errors: 446 two-team and 90 four-team episodes. Thirteen green/yellow wins had been labeled draws by the old two-team calculation. Existing generated warehouses remain untouched; rebuild them to obtain corrected tables.
- No hosted evaluation, upload, submission, public community write, Git push or PR was performed.

## Remaining limits

1. **Behavioral miners:** Crewrift's 5,824 distilled rows join the 12,000-row identity table, but game-version and complete replay provenance are absent. Heartleaf's source data/identity fixes need verification. A working template is not trustworthy integrated evidence.
2. **Paintbot trace tables:** outcome/identity normalization is corrected; the inherited Beacon trace parser is not a universal Stencil parser. Use the existing Stencil viewer tools for current player decisions.
3. **Statistical interpretation:** matching, power, stopping rules and paired/clustered designs remain the experiment author's responsibility. No detected difference does not prove equivalence.
4. **Hooks:** `.claude` hooks do not automatically run in Codex. Use explicit record updates there. Concurrent work on lesson buffers belongs in separate worktrees.
5. **Live contracts and historical evidence:** re-resolve live state at use; dated line numbers/commands can be stale even when their file links resolve. The [TODO](../../TODO.md) carries concrete provenance and authenticated-readback follow-ups.
