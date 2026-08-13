# IT235 Incident Command

Deployment is managed on the Firebolt VPS.

An online, platform-agnostic troubleshooting simulation for a 60-minute classroom session.

## Current version

The current version is a self-hosted classroom game with a small VPS backend. It includes:

- Four incident phases: triage, evidence, response, and debrief
- Team name and answer persistence in the browser
- Shared team registration, readiness, and submissions through the VPS backend
- Facilitator console at `?mode=facilitator` for releasing phases to every team
- Evidence selection, hypothesis writing, response planning, verification, and incident reporting
- A 100-point process rubric: 15 + 25 + 25 + 35
- Responsive layout for projector, laptop, and student devices

## Classroom use

Live game: https://incident.fireboltservices.com/

Facilitator console: https://incident.fireboltservices.com/?mode=facilitator

1. Open the game URL for student teams.
2. Open the same URL with `?mode=facilitator` on the projected instructor computer.
3. Have teams submit their names and members, then submit each phase when ready.
4. Use the facilitator PIN configured in the bound Apps Script to release phases 1–4 together.

The VPS stores teams, submissions, and facilitator state in a private SQLite database. The student and facilitator pages use same-origin API requests, so no Google account or spreadsheet access is required.
