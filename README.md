# Gym Log

Gym Log is a local-first workout tracker built with FastAPI and a static frontend. It stores exercises and workouts in JSON files, logs set-by-set sessions, calculates training volume, and generates basic progression guidance from rep ranges and RIR-style effort signals.

## Current Scope

- FastAPI backend in [api.py]
- Static single-page frontend served from [static/index.html]
- JSON persistence via [main.py]
- Volume analytics via [volume_engine.py]
- Progression suggestions via [progression_engine.py]

## Features

- Log workouts by exercise ID with multiple sets
- Track per-workout volume and PR flags
- View workout history enriched with exercise metadata
- See daily volume, rolling load insights, and exercise progress history
- Generate progression recommendations based on rep ranges and set effort
- Save per-exercise suggested weights
- Support legacy flat workout entries and newer set-array entries

## Project Layout

```text
.
├── api.py                  # FastAPI app and REST endpoints
├── main.py                 # JSON load/save helpers and legacy CLI
├── exercises.json          # Exercise catalog
├── workouts.json           # Workout log (+ suggestions in newer format)
├── progression_engine.py   # Rep-range and RIR progression logic
├── volume_engine.py        # Volume, ACWR, and trainer insight calculations
├── static/
│   ├── index.html          # Frontend shell
│   ├── app.js              # Client logic
│   └── styles.css          # Main stylesheet
└── *_test.py               # Test files
```

## Data Model

Exercises are stored in `exercises.json` with fields like:

```json
{
  "id": 1,
  "name": "Barbell Bench Press",
  "muscle_group": "Chest",
  "equipment": "Barbell",
  "difficulty": "Intermediate",
  "rep_range": [8, 12]
}
```

Workouts support two shapes:

Legacy format:

```json
{
  "id": 1,
  "exercise_id": 1,
  "sets": 3,
  "reps": 8,
  "weight": 185.0,
  "date": "2026-02-11T18:00:00"
}
```

Current format:

```json
{
  "id": 30,
  "exercise_id": 1,
  "sets": [
    { "reps": 10, "weight": 185.0 },
    { "reps": 8, "weight": 205.0, "rir": 1 }
  ],
  "rep_range": [8, 12],
  "date": "2026-03-11T19:15:09.559101",
  "is_pr": false,
  "volume": 3490.0
}
```

`workouts.json` can also be upgraded to an object wrapper:

```json
{
  "workouts": [],
  "suggestions": {
    "1": 140.0
  }
}
```

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
uvicorn api:app --reload
```

4. Open `http://127.0.0.1:8000/`.

The app also exposes Swagger docs at `http://127.0.0.1:8000/docs`.

## API Overview

Core endpoints currently implemented in [api.py](/Users/oscarcabezas/Desktop/gym-log/api.py):

- `GET /api`
- `GET /api/exercises`
- `GET /api/workouts`
- `POST /api/workouts`
- `PUT /api/workouts/{workout_id}`
- `DELETE /api/workouts/{workout_id}`
- `PATCH /api/exercises/{exercise_id}/suggestion`
- `GET /api/volume/today`
- `GET /api/volume/insights`
- `GET /api/volume/history?days=28`
- `GET /api/volume/exercise/{exercise_id}/progress`

Example workout payload:

```json
{
  "exercise_id": 1,
  "sets": [
    { "reps": 10, "weight": 185.0, "rir": 2 },
    { "reps": 10, "weight": 185.0, "rir": 1 }
  ],
  "rep_range": [8, 12]
}
```

## Progression Logic

The progression engine currently does three things:

- Flags a load increase when all sets hit the top of the rep range and logged RIR values are not above 2
- Suggests the next weight based on muscle group and equipment increments
- Adds RIR alerts for sets that were too easy or failed before the minimum target reps

## Analytics Logic

The volume engine currently provides:

- Total volume by muscle group
- Calendar week comparison
- Rolling acute/chronic workload ratio
- Weekly hard sets per muscle
- Daily volume history for charting
- Exercise-specific weight and volume history
- Trainer-style imbalance and overtraining warnings

## Tests

Test files exist for the API, progression engine, and volume engine:

```bash
python -m pytest
```

In the current workspace, `pytest` is not installed into the active interpreter, so I could not run the suite here without first installing dependencies.

## Known Gaps

- [main.py](/Users/oscarcabezas/Desktop/gym-log/main.py) still contains a legacy CLI flow that does not match the newer set-array workout schema.
- [volume_engine_test.py](/Users/oscarcabezas/Desktop/gym-log/volume_engine_test.py) appears out of sync with the current `rolling_window_volume()` response shape.
- [static/index.html](/Users/oscarcabezas/Desktop/gym-log/static/index.html) contains a large inline stylesheet even though [static/styles.css](/Users/oscarcabezas/Desktop/gym-log/static/styles.css) also exists, which makes frontend styling harder to maintain.

## Roadmap

- Replace JSON persistence with a database
- Remove or modernize the legacy CLI path
- Align test coverage with the current analytics response shapes
- Add stronger validation for workout updates and data migrations
- Expand dashboard visualizations and progression recommendations
