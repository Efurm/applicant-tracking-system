# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

---

## 2026-11-01 — Grilled the project idea, prototyped two decisions, wrote the PRD

### Prompts
1. `/grill-me @project-idea.md`
2. `B` (Q1, roles: Admin and Staff)
3. `A` (Q2, custom User model with a `role` field)
4. `A` (Q3, required, unique, case-insensitive email)
5. `A` (Q4, fixed source list + source details. The candidate-vs-application follow-up was not answered.)
6. `B, using the core field set above` (Q5, resume URL + core candidate fields)
7. `B,block` (Q6, edit + archive + delete-only-without-applications; archive blocked while applications in progress)
8. `A,using the field list above` (Q7, free-text department + proposed job opening fields)
9. `/prototype can you prototype from the latest question in our grill?` (for Q8, job closing rules)
10. `B,reopening allowed` (Q8, closing stops new applications only; Admins may reopen)
11. `B,admin only reopen` (Q9, forward-with-skipping stage moves, final stages locked, Admin-only reopen)
12. `run prototype on this one` (for Q10, pipeline screen layout)
13. `the page does not work properly, it loads a web page full of code`
14. `C, all-jobs list + detail` (Q10, pipeline screen)
15. `A` (Q11, stage counts on job page linking to filtered workspace)
16. `A,Y` (Q12, plain many-to-many skills + separate Admin-managed Skills page)
17. `B` (Q13, StageChange log with who/when/note)
18. `A` (Q14, user management in Django `/admin/`)
19. `A` (Q15, pytest + pytest-django)
20. `A` (Q16, `accounts` + `tracker` apps)
21. `A` (Q17, record applications from the candidate page)
22. `A` (Q18, `seed_demo` management command)
23. `/to-prd`
24. `Write this session log to PROMPTS.md according to its instructions.`

### Summary
- **Outcome:** An 18-question grill session resolved every part of `project-idea.md`, including the spec's two open questions (candidate lifecycle and job closing). Two throwaway prototypes were built in `prototypes/`: `job-closing-rules.html` (a logic demo comparing the Block, Keep-moving, and Auto-reject closing policies) and `pipeline-screen.html` (three Tailwind/DaisyUI UI variants: Kanban, sidebar + table, all-jobs list + detail). The decisions were turned into `prd/applicant-tracking-system.md`, with 68 user stories, implementation decisions, testing decisions, out-of-scope items, and notes. No application code was written, and nothing was committed.
- **Deviations:**
  - Q10 (pipeline screen): the recommendation was A (Kanban board per job). After viewing the UI prototype, the user chose C (all-jobs list + detail). That choice created a gap (no per-job overview), which led to Q11 (stage counts on the job page).
  - Q4: only the source-format part was answered. The candidate-vs-application follow-up was left blank, so the agent went with its recommendation (source stored on the application) and said the user could change it.
  - All other answers matched the agent's recommendations.
  - The user asked for prototypes twice, for Q8 and Q10, instead of answering directly.
- **Sideways:**
  - The pipeline-screen prototype was reported as "a web page full of code." The agent rendered it in headless Edge, and the screenshot showed the page working. The likely cause was the file opening as text in an editor rather than in a browser. The agent opened it with the default app and gave Open-with-Edge instructions; the user then reviewed it successfully.
  - The first headless Edge screenshot attempt produced no image. A retry with a separate browser profile worked.
  - Node.js isn't installed, so the JavaScript in the prototypes couldn't be syntax-checked locally. The job-closing prototype was handed over untested in a browser.
  - The Kanban variant's last column was cut off at 1400px width, which was noted as evidence of that layout's width problem.