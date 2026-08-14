# IT235 Incident Command

Deployment is managed on the Firebolt VPS.

An online, platform-agnostic troubleshooting simulation for a 60-minute classroom session.

## Current version

The current version is a self-hosted classroom game with a small VPS backend. It includes:

- Four incident phases: triage, evidence, response, and debrief
- Team name and answer persistence in the browser
- Shared team registration and submissions through the VPS backend
- Manual classroom advance controls on every active student screen
- Evidence selection, hypothesis writing, response planning, verification, and incident reporting
- A 100-point process rubric: 15 + 25 + 25 + 35
- Responsive layout for projector, laptop, and student devices

## Classroom use

Live game: https://incident.fireboltservices.com/

1. Open the game URL for student teams.
2. Have teams submit their names and members.
3. When the class discussion is complete, each team uses **Manual advance to next stage** on its own screen.

The VPS stores teams and submissions in a private SQLite database. The game uses same-origin API requests, so no Google account or spreadsheet access is required.
