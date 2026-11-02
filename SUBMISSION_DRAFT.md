# Devpost Submission — DRAFT (verify against the live deployed project)

## Project title
**Threadform — Design With Intent**

## One-line pitch
A personal garment design studio that turns style preferences into editable garment specifications, supports controlled visual revisions, and connects approved designs to Perfect Corp.'s YouCam Clothes V4 virtual try-on API.

## Inspiration
A person may know approximately what they want to wear, yet struggle to express details such as a muted greenish-blue fabric with very small black checks. Generic AI image revisions can also alter unrelated features. Threadform explores a design workflow that keeps the user's intended garment properties visible and editable throughout the process.

## What it does
- Users can start with optional context such as occasion, preferred aesthetic and budget, or skip the form.
- The studio maintains a structured garment specification rather than relying on a prompt alone.
- The reference shirt editor lets users change fabric color, check/stripe color, check scale and pattern type while preserving the original reference garment's geometry.
- A conservative text-command parser supports selected revisions and reports unsupported requests.
- An explicit consent-driven photo upload starts a real YouCam Clothes V4 garment try-on job when API credentials are configured.
- Users can export a garment brief for subsequent shopping or discussion with a tailor.

## How YouCam is used
The backend registers the user and garment image files via the official YouCam file API (`POST /s2s/v2.0/file`), uploads bytes to the provider's presigned storage URLs, creates an asynchronous job via `POST /s2s/v2.0/task/cloth-v4`, and polls the corresponding GET task endpoint for completion. The app does not fabricate VTO images or claim they are dimensionally exact.

**This integration is implemented and unit-tested against mocked HTTP responses. Before submitting, configure a valid API key, perform a live request and verify the provider-generated image appears. Until that happens, do not claim the live integration has been verified.**

## Technical stack
FastAPI / Python, HTML/CSS/JavaScript, Pillow, NumPy, YouCam Clothes V4 REST API. Server-side environment variables protect the provider key.

## Why it matters
The goal is to provide more control over fashion visualizations—not enforce any single aesthetic, fashion trend, body standard, or price tier. Tailoring and ready-made shopping are two potential downstream paths; this prototype does not pretend to implement ecommerce matching or production-ready garment patterns.

## Work still required before a valid submission
- [ ] Obtain and configure a real `YOUCAM_API_KEY` via environment variables.
- [ ] Demonstrate a successful real YouCam task with an authorized full-body photo.
- [ ] Deploy the app and test the public URL.
- [ ] Create and link a public GitHub repository.
- [ ] Record a public 1–3 minute video demonstrating the real implementation.
- [ ] Fill the required Devpost entry sections and submit before the deadline.

## Suggested 90-second demo structure
00–12s: Introduce the frustration of communicating detailed garment preferences.
12–30s: Demonstrate guided context, structured garment properties and the edited check shirt.
30–46s: Run one controlled change, explain which property changed, and show undo.
46–70s: On a configured deployment, upload an authorized photo and **actually run** YouCam Clothes V4. If it does not complete, do not splice in a simulated output.
70–82s: Show the actual result (if available) and exported design brief.
82–90s: Mention limitations: approximate visual representation, not exact fit or manufacturability.

Official challenge: https://youcam-api-skin-ai-ecommerce.devpost.com/
