# IT235 Incident Command

Deployment is managed through GitHub Pages.

An online, platform-agnostic troubleshooting simulation for a 60-minute classroom session.

## Current version

This first version is a polished static prototype for GitHub Pages. It includes:

- Four incident phases: triage, evidence, response, and debrief
- Team name and answer persistence in the browser
- Evidence selection, hypothesis writing, response planning, verification, and incident reporting
- A 100-point process rubric: 15 + 25 + 25 + 35
- Responsive layout for projector, laptop, and student devices

## Important next step

GitHub Pages is static, so this prototype stores answers locally in each browser. For a real classroom deployment, the next iteration should connect the submit buttons to a shared backend such as Google Forms/Sheets, Supabase, or a small serverless endpoint. That will let the facilitator see submissions from every team on a live board.
