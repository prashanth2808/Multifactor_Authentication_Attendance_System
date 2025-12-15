# MFA – Face & Voice Attendance System

A biometric attendance and session management system that uses face recognition (ArcFace) with optional voice verification (ECAPA-TDNN). It supports a Typer-based CLI and a Flask web UI for registration, session (login/logout), and admin reporting. MongoDB stores users and daily sessions.

Key highlights
- Face recognition: InsightFace (RetinaFace detection + ArcFace embeddings)
- Voice verification (optional): SpeechBrain ECAPA-TDNN
- Session tracking with a 9-hour rule and Day Label classification
- CLI + Flask UI
- Works offline with local MongoDB

- Day Label: Sessions are now labeled and stored as:
  - < 4 hrs → Half Day
  - 4–8 hrs → Half Day
  - ≥ 8 hrs → Full Day
- Label is persisted on logout and auto-absent, and shown in CLI Admin (today, logs). Frontend wiring can be enabled in Flask templates if desired.

Directory layout
- app.py — Flask app (registration/session/admin pages)
- main.py — Typer CLI entrypoint (register/session/report/admin)
- config/settings.py — App configuration (reads .env)
- db/ — Mongo client and repositories (users, sessions)
- services/ — Face/voice detection & embedding, comparison, registration
- utils/ — Camera, image preprocessing, email utils
- templates/ — Flask Jinja templates
- static/ — CSS/JS assets
- models/ — ArcFace ONNX model (w600k_r50.onnx)
- pretrained_models/spkrec-ecapa-voxceleb — SpeechBrain checkpoints

Prerequisites
- Python 3.9+
- MongoDB (local or remote). Default: mongodb://localhost:27017
- Webcam for face capture; microphone for voice (optional)
- Windows/Linux/macOS supported (CPU by default)

Setup
1) Clone or copy this project
2) Create and activate a virtual environment
3) Install dependencies:
   - pip install -r requirements.txt
   - For Flask UI or voice features, also:
     - pip install -r requirements_flask.txt
4) Configure .env (create if missing):
   - MONGODB_URI=mongodb://localhost:27017
   - DB_NAME=face_attendance
   - SIMILARITY_THRESHOLD=0.62
   - LIVENESS_REQUIRED=false
   - LOG_LEVEL=INFO

Running
- CLI (recommended for quick test):
  - Register a user:
    - python main.py register --name "Full Name" --email user@example.com --user-type student --class "A1"
  - Start a session (login/logout):
    - python main.py session
  - Admin views:
    - python main.py admin today
    - python main.py admin logs --date YYYY-MM-DD
  - Reports:
    - python main.py report --today

- Flask web UI:
  - python app.py
  - Open http://localhost:5000
  - Pages: Registration, Session, Admin
  - Note: If Day Label is not visible yet in UI tables, enable it by adding the `day_label` field to the admin/session templates.

How it works (high-level)
- Registration: Captures 3 face images via webcam; computes ArcFace embeddings; optional voice embedding. Stores in MongoDB with metadata.
- Session (login/logout): Detects face, matches via cosine similarity (threshold from settings). The second scan within 9 hours logs out and finalizes the session; if no logout occurs, the system auto-marks absent after 9 hours.
- Day Label: When a session is finalized (logout or auto-absent), the system computes and stores `day_label` using duration_minutes. Older sessions without `day_label` are computed on the fly in reports.

Configuration
- Thresholds: SIMILARITY_THRESHOLD (default 0.62)
- Timezone: IST (Asia/Kolkata) defaults in session repo
- Models: models/w600k_r50.onnx for face; SpeechBrain checkpoints for voice

Troubleshooting
- MongoDB connection failed:
  - Ensure MongoDB is running and MONGODB_URI is reachable
  - Check firewall/localhost access
- Webcam not found:
  - Verify camera permissions and device index (utils/camera.py)
- Slow inference on CPU:
  - Reduce camera resolution, ensure Release build of onnxruntime, or enable GPU providers
- Voice model errors:
  - Install requirements_flask.txt and verify pretrained model paths

Data model (simplified)
- Users: name, email (unique), face_embeddings (list of vectors), voice_embedding (optional), metadata, timestamps
- Sessions: user_id, login_time, logout_time, duration_minutes, day_label, status (present/absent_fault), timestamps

Security & Privacy
- All biometric data is stored locally in MongoDB by default
- Use proper access control, backups, and encryption at rest for production

Roadmap ideas
- Enforce liveness detection in face pipeline
- Add Day Label to Flask Admin and Session Result pages by default
- GPU acceleration for ONNXRuntime and InsightFace
- REST API endpoints for mobile capture clients

License
- Internal/educational use. Review third-party model licenses (InsightFace, SpeechBrain) before distribution.

Contact
- Maintainer: Your Team
- Issues/Support: Open a ticket or reach out to the maintainer
