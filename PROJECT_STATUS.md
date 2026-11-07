# Project status

## Completed phases

1. Workspace and environment inspected. Python 3.12, Node 20, npm, Docker, and the MySQL client were already installed. The system MySQL service is inactive, so MySQL 8 runs in Docker.
2. Monorepo created: frontend, backend, tests, docs, Compose, and env example.
3. MySQL schema applied with Alembic revisions `001_initial` and `002_user_phone`. Tables: users, user_sessions, password_reset_tokens, puzzles, puzzle_cells, puzzle_solutions, solution_positions. Users store country ISO, dial code, national number, and E.164 phone. Existing rows stay null; new signups require a phone. The running API uses Aiven MySQL service `cat-puzzle-mysql` (database `defaultdb`) with the project CA certificate. The connection string and certificate stay out of git.
4. Authentication: signup, login, logout, me, profile update, change password, forgot/reset password, email verification endpoint. Argon2 hashes. JWT in an HTTP-only cookie. Login throttling. Ownership checks. Signup phone numbers are checked against the country list.
5. Dashboard, upload, history, profile, and the puzzle workspace.
6. Upload validation for PNG, JPEG, and WEBP, with size limits, preview, and progress.
7. OpenCV grid detection, Lab color clustering, X and cat marks, perspective recovery, confidence, and no invented cells.
8. Board editor for colors, blocked cells, existing cats, rules, and dimensions.
9. Constraint solver with propagation, minimum remaining values, forward checking, and a separate validator.
10. Solution grid, placement table, image overlay, copyable instructions, and download.
11. Puzzle history stored per user and isolated from other accounts.
12. Pytest and Vitest run and passing. Live MySQL flow and browser flow checked.
13. Dockerfiles and Compose written. Image build is the last verification step.
14. README, vision notes, solver notes, and AWS deployment design. Nothing was deployed to AWS.

## Current phase

Complete. The app is running locally and through Docker Compose.

## Implemented features

- Account signup and login with a session cookie
- Signup stores a phone number with a searchable country calling code. The account page shows the stored number.
- Screenshot upload and local grid reading
- Manual correction before solving
- Unique, multiple, and impossible outcomes
- Saved history scoped to the logged-in user

## Test results

- Pytest: 25 passed
- Vitest: 6 passed
- Live API against MySQL: signup, 6×6 detection with the expected blocked cells, 20 validated solutions, solution PNG, history, and a 404 for a second user
- Browser: signup reached the dashboard, logout returned to login, login reopened a solved puzzle, the cell editor showed the blocked X, and solution switching worked

## Known issues

- Password reset email is logged when SMTP is unset. `DEBUG_RETURN_TOKENS` is true only in the local `.env`. Set it false before any shared deploy.
- Login throttling is per process, not shared across API workers.
- Uploads stay on disk. S3 is described in `docs/aws-deployment.md` and is not wired up.
- Very pale cell colors can be mistaken for gaps. The editor is the recovery path.
- The solver stops at 20 solutions by default, so “multiple” can mean “at least 20.”
- `npm audit --omit=dev` reports two moderate React Router advisories. This app does not use the SSR error deserializer, and it does not pass untrusted paths into `<Link>`.

## Docker

`docker compose build` succeeded. `docker compose up -d` is running:

- http://127.0.0.1:8080 returns the site and proxies `/api/health`
- http://127.0.0.1:8000/api/health returns ok
- MySQL, backend, and frontend containers are up

Port 8000 is the Compose backend. Stop that container before starting a second uvicorn on the same port.

## Next tasks

- Point storage at S3 when you approve an AWS deploy
- Turn on SMTP and require email verification in production
