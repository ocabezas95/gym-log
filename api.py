from fastapi import FastAPI
from pydantic import BaseModel, field_validator
from fastapi import HTTPException
from main import load_workouts, save_workouts, load_exercises, save_exercises
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from datetime import datetime
from datetime import date
from volume_engine import HybridVolumeEngine
from progression_engine import ProgressionEngine

from typing import List, Optional

app = FastAPI()


class SetEntry(BaseModel):
    reps: int
    weight: float
    rir: Optional[int] = None


class Workout(BaseModel):
    exercise_id: int
    sets: List[SetEntry]
    rep_range: Optional[List[int]] = None


class SuggestionUpdate(BaseModel):
    suggested_weight: float

    @field_validator("suggested_weight")
    @classmethod
    def must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("suggested_weight must be non-negative")
        return v


@app.get("/api")
def home():
    return {"message": " Gym Tracker API is running!"}


@app.get("/api/exercises")
def get_exercises():
    return load_exercises()


@app.get("/api/workouts")
def get_workouts():
    workouts = load_workouts()
    exercises = load_exercises()

    enriched = []
    for w in workouts:
        exercise = next(
            (e for e in exercises if e["id"] == w["exercise_id"]), None)
        if exercise:
            enriched.append({
                **w,
                "exercise_name": exercise["name"],
                "muscle_group": exercise["muscle_group"],
                "difficulty": exercise["difficulty"],
                "equipment": exercise["equipment"]
            })

        else:
            # If exercise not found, just return workout as is
            enriched.append(w)

    return enriched


@app.get("/api/volume/today")
def get_today_volume():
    workouts = load_workouts()
    today_str = date.today().isoformat()
    today_workouts = [w for w in workouts if w["date"].startswith(today_str)]
    total_volume = sum(w.get("volume", 0) for w in today_workouts)
    return {"date": today_str, "total_volume": total_volume}


@app.get("/api/volume/insights")
def get_volume_insights():
    engine = HybridVolumeEngine(load_workouts(), load_exercises())
    return engine.generate_stats()


@app.get("/api/volume/history")
def get_volume_history(days: int = 28):
    engine = HybridVolumeEngine(load_workouts(), load_exercises())
    return engine.daily_volume_history(days)


@app.get("/api/volume/exercise/{exercise_id}/progress")
def get_exercise_progress(exercise_id: int):
    engine = HybridVolumeEngine(load_workouts(), load_exercises())
    return engine.exercise_weight_history(exercise_id)


@app.post("/api/workouts")
def add_workout(workout: Workout):
    exercises = load_exercises()
    workouts = load_workouts()
    exercise = next(
        (e for e in exercises if e["id"] == workout.exercise_id), None)

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    next_id = max((w["id"] for w in workouts), default=0) + 1

    sets_data = [s.model_dump() for s in workout.sets]
    max_weight = max(s["weight"] for s in sets_data)
    volume = sum(s["reps"] * s["weight"] for s in sets_data)

    # find previous max weight for the same exercise
    previous_weights = []
    for w in workouts:
        if w["exercise_id"] != workout.exercise_id:
            continue
        if isinstance(w.get("sets"), list):
            for s in w["sets"]:
                previous_weights.append(s.get("weight", 0))
        elif "weight" in w:
            previous_weights.append(w["weight"])

    is_pr = previous_weights and max_weight > max(previous_weights)

    new_workout = {
        "id": next_id,
        "exercise_id": workout.exercise_id,
        "sets": sets_data,
        "rep_range": workout.rep_range,
        "date": datetime.today().isoformat(),
        "is_pr": is_pr,
        "volume": volume
    }

    progression = ProgressionEngine(exercises).analyze(new_workout)
    new_workout["progression"] = progression

    workouts.append(new_workout)
    save_workouts(workouts)

    return {"workout": new_workout, "progression": progression}


@app.put("/api/workouts/{workout_id}")
def update_workout(workout_id: int, updated_workout: Workout):
    workouts = load_workouts()

    for workout in workouts:
        if workout["id"] == workout_id:
            workout["exercise_id"] = updated_workout.exercise_id
            sets_data = [s.model_dump() for s in updated_workout.sets]
            workout["sets"] = sets_data
            workout.pop("reps", None)
            workout.pop("weight", None)
            workout["volume"] = sum(s["reps"] * s["weight"] for s in sets_data)
            save_workouts(workouts)
            return workout

    raise HTTPException(status_code=404, detail="Workout not found")


@app.delete("/api/workouts/{workout_id}")
def delete_workout(workout_id: int):
    workouts = load_workouts()
    workout_to_delete = next(
        (w for w in workouts if w["id"] == workout_id), None)

    if workout_to_delete is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    workouts.remove(workout_to_delete)
    save_workouts(workouts)

    return {"message": "Workout deleted successfully"}


@app.patch("/api/exercises/{exercise_id}/suggestion")
def update_suggestion(exercise_id: int, body: SuggestionUpdate):
    exercises = load_exercises()
    exercise = next((e for e in exercises if e["id"] == exercise_id), None)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    exercise["suggested_weight"] = body.suggested_weight
    save_exercises(exercises)
    return {"id": exercise_id, "suggested_weight": body.suggested_weight}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
