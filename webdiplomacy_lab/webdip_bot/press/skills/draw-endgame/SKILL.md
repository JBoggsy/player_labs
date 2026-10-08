---
name: draw-endgame
description: Play for the draw-share score in the last two years before the year cap.
---
# Draw-share endgame

The game ends as a draw after the cap year's autumn. Score = your centres squared over
the sum of all survivors' centres squared.

- Every centre you add near the end is worth more than any promise you keep. In the final
  autumn, the reputation value of keeping a promise is gone.
- Taking a centre from the **leader** raises your share twice: you grow and their square
  shrinks. Prefer leader centres with `center_values`.
- Do not leave home centres empty in the final autumn; set `risk` to 0.5 or higher if a
  neighbour can reach them.
- Eliminating a small power barely changes your share. Growth does.
