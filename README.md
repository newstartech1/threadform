# Threadform — Design Integrity × YouCam Clothes V4

A lean, runnable prototype for the **Perfect Corp. YouCam API Skin AI & eCommerce VTO Hackathon 2026**.

The app turns a visual garment reference into a structured design, supports controlled color/pattern changes, offers a short guided brief and free-form edits, and sends a wearer photograph plus garment reference to the **actual** YouCam Clothes V4 API. It then polls for the result. It never fabricates an API result.

## What is implemented
- Responsive design-studio frontend with guided occasion/style/budget fields.
- A fixed-geometry photographic shirt preview with deterministic recoloring and check/pinstripe/solid rendering.
- Design version history, undo, editable fields, text-based command parser, and exportable brief.
- Server-side YouCam Clothes V4 file registration, presigned upload, task creation, and status polling.
- Browser photo selection; photos uploaded to Perfect Corp only after clicking **Start real try-on**.
- Honest fallback for missing API credentials, provider errors, and incomplete try-on tasks.

## Scope and truthful limitations
- The preview editor is a **deterministic image-manipulation proof of concept**, not a generative fashion model. It fixes garment silhouette and uses the pre-approved shirt photo from this project. Collar/fit text fields are recorded but NOT visually reconstructed.
- A VTO preview is visual, not a precise fit, fabric simulation, or manufacturing pattern.
- A fully usable implementation requires valid YouCam API credentials and sufficient credits; without them, the app can still run its local preview/editor but cannot produce VTO results.
- VTO results are temporary provider URLs. The app doesn't store person photos or task results in a database.
- The browser stores the editable brief and revisions locally; do not enter sensitive personal information.
- Complex patterned garment photo inputs might not preserve every micro-check. This is why the app labels its preview appropriately and does not claim verified visual fidelity.

## Run locally (Windows PowerShell)
```powershell
cd threadform
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:YOUCAM_API_KEY="YOUR_TOKEN_FROM_YOUCAM_CONSOLE"
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. The app works without the token for preview and editor; the YouCam button will explain it requires credentials.

Linux/macOS:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export YOUCAM_API_KEY="YOUR_TOKEN_FROM_YOUCAM_CONSOLE"
uvicorn app.main:app --reload
```

## Deployment (Vercel)
1. Create a **new private or public repository** for the project and push all non-secret files.
2. In Vercel, import the repository using Python / `vercel.json`.
3. Set `YOUCAM_API_KEY` in Vercel project environment variables; optionally set `YOUCAM_API_BASE` to the official region-specific domain.
4. Redeploy. Confirm `/api/health` reports `youcam_configured: true`.
5. Upload a valid full-body JPG/PNG photo and start an actual try-on.
6. Confirm the task completes and displays a provider image before calling the integration working in a demo.

**Important:** No live deployment, GitHub push, real API request, demo video, or Devpost submission has been performed by this code package.

## API routes
- `GET /api/health` configuration status only; no tokens returned.
- `POST /api/preview` `{"design": {...}}` -> rendered JPEG.
- `POST /api/edit` `{"design": {...}, "instruction": "smaller black checks"}` -> new structured design.
- `POST /api/tryon` multipart: `person`, optional `garment`, `design_json`. Uploads photo and garment to Perfect Corp (only with configured credentials), returns a task ID.
- `GET /api/tryon/{task_id}` -> task status / result URL, via provider.

## Security and privacy
- API tokens live only on the server, via environment variables, never browser code or Git.
- User photos are held in request memory and transferred to Perfect Corp for processing when a user explicitly initiates VTO.
- Uploaded image type/size is validated. No arbitrary user-specified proxy URLs.
- This is a hackathon prototype: production must add auth, per-user quotas, consent/privacy policy, deletion and abuse protections.

## Source documentation
- https://docs.perfectcorp.com/reference/ai_clothes/section/overview/integration-guide
- https://docs.perfectcorp.com/reference/ai_clothes/v4.0/paths/~1s2s~1v2.0~1task~1cloth-v4/post
- https://youcam-api-skin-ai-ecommerce.devpost.com/rules

## Suggested honest demo
1. Open studio with the greenish-blue shirt with black checks.
2. Edit pattern scale and color; show undo and design attributes.
3. Upload a permitted full-body photo.
4. Click **Start real try-on** and demonstrate a returned YouCam image (only if API has been successfully configured and run).
5. Download design brief and explain the limitations.
