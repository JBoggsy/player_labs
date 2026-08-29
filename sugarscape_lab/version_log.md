# Sugarscape policy version log

Record every upload as `name:version`, immutable version ID, source state,
strategy, and the experience request or league submission that used it.

| Policy version | Version ID | Strategy | Evaluation |
| --- | --- | --- | --- |
| `sugarscape-abundance:v1` | `c0801ce6-cf08-4823-823b-f3361d9a1646` | Maximize metabolism-adjusted harvest runway, then raw abundance | `xreq_851a44c5-5cfd-4ba7-b35f-8dc4920a3aef`, `xreq_fe3052d0-5031-458f-bc27-43953807ed3e` |
| `sugarscape-longevity:v1` | `6147540f-5646-46ce-a798-e75019d86138` | Maximize the weaker post-harvest resource runway | `xreq_851a44c5-5cfd-4ba7-b35f-8dc4920a3aef`, `xreq_d4ec1ca1-a237-4ea0-bf1e-b574a9aaf304` |
| `sugarscape-health:v1` | `a6dcdc7a-fdbc-48d4-b67e-fbeef87e9349` | Minimize pollution above an explicit survival floor | `xreq_fe3052d0-5031-458f-bc27-43953807ed3e`, `xreq_d4ec1ca1-a237-4ea0-bf1e-b574a9aaf304` |
| `sugarscape-greedy:v1` | `1ae78a82-1e40-4462-9a34-aaed9fa7aee0` | Canonical bundled `candidates[0]` baseline from `coworld-sugarscape@f085d42` | Canonical certification policy; submission pending league creation |
| `sugarscape-longevity:v2` | `da5b1bad-0885-42f0-a51f-8c004ed7d255` | Byte-identical v1 image re-uploaded under Games Bond | Sugarscape submission `sub_4c44545e-c992-4a18-8ca7-8d068f37110e` |
| `sugarscape-health:v2` | `8cfbe0e2-ce78-4bec-bec4-700ece4af9b5` | Byte-identical v1 image re-uploaded under seedtest-cx3-delegator | Sugarscape submission `sub_9033b664-79d4-4eac-a8ea-c327a5f3a326` |
| `sugarscape-greedy:v2` | `4e28d11b-b638-45df-8d9e-b35f36b1c90c` | Byte-identical v1 image re-uploaded under seedtest-cx3-newcomer | Sugarscape submission `sub_7eca2d44-88dc-4e04-bdcd-8eb10428d28d` |

`sugarscape-abundance:v1` was submitted under James Botts as
`sub_9bad3c48-89a8-4f4f-aa72-aa6a0b498bea`. The v2 re-uploads were necessary
because policy versions are assigned to the player active at upload time.

After the league's `players_per_user` limit increased to 2, abundance v1 was
resubmitted as `sub_b89cb71f-0baf-49e1-8f69-d0faac1ec69a` and longevity v2 as
`sub_7493242d-e370-43a6-bbc9-f8304055a7a9`. Both resulting memberships qualified
and became their respective players' champions.
