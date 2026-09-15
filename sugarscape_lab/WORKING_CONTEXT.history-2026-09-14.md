# Working context

## Objective

Build and compare three unique Sugarscape population policies with different
high-level approaches to improving happiness through the movement information
the game actually exposes.

## Mechanics contract

- One policy socket controls every agent assigned to its decision-model labels.
- Each request permits exactly one candidate cell; invalid or late actions fall
  back to the game's greedy candidate after 100 ms by default.
- Movement is the only player action. Collection, metabolism, trade,
  reproduction, combat, disease, aging, and happiness updates remain in-game.
- Happiness is the sum of conflict, family, health, social, and relative-wealth
  terms, but the player observation exposes only movement candidates and a
  subset of the active agent state.
- Hosted policy score is final living population sugar plus spice. Population,
  mean wealth, fallbacks, and global final statistics are additional signals.

## Initial hypotheses

1. Abundance-first movement should raise wealth happiness and hosted score but
   may overconsume one resource or tolerate pollution.
2. Balanced resource runway should keep more agents alive and improve sustained
   health/wealth even when it gives up immediate yield.
3. Pollution-aware movement should protect health, especially for sick agents,
   if the resource safety floor prevents starvation.

Each policy logs why its selected candidate differed from the built-in greedy
choice so a flat result can distinguish non-activation from ineffectiveness.

## Active evaluation

The v1 pairwise matrix was created on 2026-08-05 against canonical
`sugarscape:0.1.4`; each 16-episode request alternates both seat orders:

- abundance vs longevity: `xreq_851a44c5-5cfd-4ba7-b35f-8dc4920a3aef`
- abundance vs health: `xreq_fe3052d0-5031-458f-bc27-43953807ed3e`
- longevity vs health: `xreq_d4ec1ca1-a237-4ea0-bf1e-b574a9aaf304`

All 48 episodes completed successfully with zero fallbacks. See
[`evals/v1-results.md`](evals/v1-results.md). No pairwise score delta was
statistically distinguishable from zero at 16 episodes. The actionable finding
is mechanical: the default configuration disables spice, pollution, and disease,
so longevity and health need distinct default-world tie-break behavior before a
larger replication is worthwhile.

## Submission state

James authorized submitting all three v1 policies plus the canonical greedy
baseline under four distinct players. All four submissions were placed in
Sugarscape league `league_620a74a7-eb1f-4386-b386-0e7246be4eb6` on 2026-08-05:

- abundance v1: James Botts, `sub_9bad3c48-89a8-4f4f-aa72-aa6a0b498bea`
- longevity v2: Games Bond, `sub_4c44545e-c992-4a18-8ca7-8d068f37110e`
- health v2: seedtest-cx3-delegator, `sub_9033b664-79d4-4eac-a8ea-c327a5f3a326`
- greedy v2: seedtest-cx3-newcomer, `sub_7eca2d44-88dc-4e04-bdcd-8eb10428d28d`

The account was already at its 12-player identity limit, so existing identities
were reused. Longevity, health, and greedy required byte-identical v2 re-uploads
while their assigned player sessions were active; a policy version cannot be
submitted as a player other than the one assigned at upload.

The league setting `players_per_user` is enforced against the owning user, not
the player identity. Its initial value of 1 caused each later placement to evict
the prior membership with `status=disqualified, substatus=inactive`; those were
administrative evictions rather than qualification failures.

On 2026-08-05 the limit was raised to 2 without changing the rest of the league
settings. Abundance v1 was resubmitted under James Botts as
`sub_b89cb71f-0baf-49e1-8f69-d0faac1ec69a`, producing competing champion
membership `lpm_99d5a860-7f5b-430d-bb2f-61562f2ab979`. Longevity v2 was
resubmitted under Games Bond as `sub_7493242d-e370-43a6-bbc9-f8304055a7a9`,
producing competing champion membership
`lpm_d9ee86d8-0a07-44e0-9840-c850f8ac53a6`. Greedy was evicted as expected, so
the two active memberships are now Abundance and Longevity.
