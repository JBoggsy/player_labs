---
name: negotiation
description: How to make, test and record deals (DMZs, supports, spheres of influence).
---
# Negotiation playbook

1. **Find who matters this phase.** Neighbours whose units can reach your centres, and
   powers whose support would win you a contested centre. Use `board` and `predict`.
2. **Make one concrete offer per power.** Good forms:
   - DMZ: "Neither of us moves into GAL or TYR this phase."
   - Support: "If you order A BUD S A VIE - GAL, I order F TRI S A BUD - SER."
   - Sphere: "You take the north (SWE, NWY); I stay out. I take the south."
3. **Test it before you send it.** `assess_deal(power, their_orders, our_orders, our_forbidden)`.
   Offer only deals where "both_honour" beats your current committed plan and "they_betray"
   is survivable.
4. **When they agree, record it.** `record_commitment` for their side and for yours
   (`power="ME"`). Then `commit_orders` with: stance ally, their promised orders in
   `expected_orders`, your promised orders in `require_orders`, the DMZ in `forbid_moves_into`.
5. **Follow up on verdicts.** If a promise was broken, lower trust in your note on that
   power, set its stance to neutral or hostile, and say so briefly. If kept, raise trust.
