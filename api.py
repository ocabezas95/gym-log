from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import HTTPException
from main import load_workouts, save_workouts, load_exercises
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from datetime import date

app = FastAPI()


class Workout(BaseModel):
    exercise_id: int
    sets: int
    reps: int
    weight: float


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


@app.post("/api/workouts")
def add_workout(workout: Workout):
    exercises = load_exercises()
    workouts = load_workouts()
    exercise = next(
        (e for e in exercises if e["id"] == workout.exercise_id), None)

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    next_id = max((w["id"] for w in workouts), default=0) + 1

    # find previous max weight for the same exercise
    previous_weights = [w["weight"]
                        for w in workouts if w["exercise_id"] == workout.exercise_id]

    is_pr = bool(previous_weights) and workout.weight > max(previous_weights)

    # workout volume calculation (v = sets * reps * weight)
    volume = workout.sets * workout.reps * workout.weight

    new_workout = {
        "id": next_id,
        "exercise_id": workout.exercise_id,
        "sets": workout.sets,
        "reps": workout.reps,
        "weight": workout.weight,
        "date": datetime.today().isoformat(),
        "is_pr": is_pr,
        "volume": volume
    }

    workouts.append(new_workout)
    save_workouts(workouts)

    return new_workout


@app.put("/api/workouts/{workout_id}")
def update_workout(workout_id: int, updated_workout: Workout):
    workouts = load_workouts()

    for workout in workouts:
        if workout["id"] == workout_id:
            workout["exercise_id"] = updated_workout.exercise_id
            workout["sets"] = updated_workout.sets
            workout["reps"] = updated_workout.reps
            workout["weight"] = updated_workout.weight
            # Recalculate volume
            workout["volume"] = workout["sets"] * \
                workout["reps"] * workout["weight"]
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


app.mount("/", StaticFiles(directory="static", html=True), name="static")
