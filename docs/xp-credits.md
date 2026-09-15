# Experience-request credits

Verified 2026-09-14 against backend source and the signed-in account's live credit meter. **Softmax grants credits; users are not billed money for XP requests.** Hosted work consumes a limited, replenishing allowance.

## Allowance

The allowance belongs to the **owning user account**, shared across that user's players and Coworlds. A player credential uses its owner's schedule; creating another player does not create another allowance.

| Account schedule | Daily refill | Weekly total | Accumulation cap |
| --- | ---: | ---: | ---: |
| Standard user | 500 / 7 ≈ 71.43 credits | 500 credits | 1,000 credits |
| Softmax team member | 10,000 / 7 ≈ 1,428.57 credits | 10,000 credits | 20,000 credits |

Refills land at **00:00 UTC daily**. Unused allowance accumulates up to the cap. Ten credits represent $1 of metered infrastructure/model usage; this is an accounting conversion, **not a customer bill**. Credit cost varies with compute and LLM usage, so there is no fixed number of requests per day. League-scheduled play is credited to the league rather than the user's XP allowance.

Admission checks the estimate against balance **minus holds for active requests**; displayed balance alone does not guarantee another request fits. Actual metered use drains the balance and may exceed the estimate; running work is not killed just because the allowance runs out. Additional explicit grants may also affect the balance.

## Operating rule

Read the current balance/refill and choose a bounded batch. The public schema has no pre-create quote endpoint; `cost_preview` is returned only when creating the request, so save that response. Local schema checks are not cost quotes. Use the allowance for targeted competitive experiments, with existing evidence and local mechanism/self-play runs where appropriate. Preserve the user's no-hosted-XP-self-play preference. Do not introduce a new per-request permission gate within an already authorized experiment.

The account-only endpoint is `GET /usage/me/credits` on the Observatory gateway (`https://softmax.com/api/observatory/usage/me/credits`). Use ordinary user authentication; it requires a user credential. Its `status` object includes `balance_credits`, `refill_credits`, `refill_cadence`, `max_balance_credits`, `next_refill_at`, `credits_per_usd` and `enforced`. Re-read it rather than treating this dated table as immutable.

## Evidence and correction

Backend source: [user_credits.py at 70bcdd00](https://github.com/Metta-AI/metta/blob/70bcdd00b120ae29326b6844e792c076a7b3ae54/app_backend/src/metta/app_backend/user_credits.py). The standard schedule above is source-verified. The live signed-in team account returned refill 1,428.5714285714287, cadence `day`, cap 20,000, conversion 10 and `enforced=true`; this independently confirms the deployed team schedule. No request was created or charged to the allowance during verification.

The initial modernization incorrectly generalized an August preference's “cost money” explanation into “treat requests as paid work.” That wording missed the granted-credit system. The corrected distinction is **free to the user, limited by replenishing credits**, not unlimited/free infrastructure and not monetary billing.

`recent_requests` on the credit endpoint attributes **compute only**; do not present it as full per-request compute-plus-model cost. XP credits, continuously refilling HTTP request/complexity budgets, and job concurrency caps are separate; see the [platform reference](platform-reference.md).
