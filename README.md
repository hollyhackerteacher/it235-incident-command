# IT235 Incident Command

Deployment is managed on the Firebolt VPS.

An online, platform-agnostic troubleshooting simulation for a 60-minute classroom session.

## Current version

The current version is a self-hosted classroom game with a small VPS backend. It includes:

- Four incident phases: triage, evidence, response, and debrief
- Individual student name and answer persistence in the browser
- Individual submissions through the VPS backend
- Guided dialogue prompts that advance after each completed response
- Evidence is presented as five separate source screens, each with a learning/hypothesis response
- A running incident notebook keeps earlier clues and individual notes visible
- Back navigation allows students to revisit earlier dialogue and evidence
- A final individual report that can be downloaded, printed, or copied for grading
- Evidence selection, hypothesis writing, response planning, verification, and incident reporting
- A 100-point process rubric: 15 + 25 + 25 + 35
- Responsive layout for projector, laptop, and student devices

## Classroom use

Live game: https://incident.fireboltservices.com/

1. Open the game URL for students.
2. Each student enters their name and begins the assignment.
3. Students respond to each dialogue prompt and submit it to continue to the next prompt.
4. At the end, each student downloads, prints, or copies the completed report for submission.

The VPS stores individual student submissions in a private SQLite database. The game uses same-origin API requests, so no Google account or spreadsheet access is required.
