# IT235 Incident Command

Deployment is managed through GitHub Pages.

An online, platform-agnostic troubleshooting simulation for a 60-minute classroom session.

## Current version

The current version is a GitHub Pages game with an optional Google Sheets classroom workspace. It includes:

- Four incident phases: triage, evidence, response, and debrief
- Team name and answer persistence in the browser
- Shared team registration, readiness, and submissions through the private classroom workspace
- Facilitator console at `?mode=facilitator` for releasing phases to every team
- Evidence selection, hypothesis writing, response planning, verification, and incident reporting
- A 100-point process rubric: 15 + 25 + 25 + 35
- Responsive layout for projector, laptop, and student devices

## Classroom use

1. Open the game URL for student teams.
2. Open the same URL with `?mode=facilitator` on the projected instructor computer.
3. Have teams submit their names and members, then submit each phase when ready.
4. Use the facilitator PIN configured in the bound Apps Script to release phases 1–4 together.

The bound Google Sheet stores the `Teams`, `Submissions`, and `Control` tabs. The Apps Script deployment is owned by `davidbowmanbyu@gmail.com`; student-facing pages do not receive access to the Sheet itself.
