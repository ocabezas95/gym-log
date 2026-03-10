from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import HTTPException
from main import load_workouts, save_workouts
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from datetime import datetime
from datetime import date

app = FastAPI()


class Workout(BaseModel):
    exercise_name: str
    sets: int
    reps: int
    weight: float


@app.get("/api")
def home():
    return {"message": " Gym Tracker API is running!"}


@app.get("/api/workouts")
def get_workouts():
    return load_workouts()

@app.get("/api/volume/today")
def get_today_volume():
    workouts = load_workouts()
    today_str = date.today().isoformat()
    today_workouts = [w for w in workouts if w["date"].startswith(today_str)]
    total_volume = sum(w.get("volume", 0) for w in today_workouts)
    return {"date": today_str, "total_volume": total_volume}


    


@app.post("/api/workouts")
def add_workout(workout: Workout):
    workouts = load_workouts()

    if workouts:
        next_id = max(w["id"] for w in workouts) + 1
    else:
        next_id = 1
    
    # find previous max weight for the same exercise
    previous_weights = [w["weight"] for w in workouts if w["exercise_name"].lower() == workout.exercise_name.lower()]

    is_pr = False
    if previous_weights:
        if workout.weight > max(previous_weights):
            is_pr = True
    else:
        is_pr = True  # First time doing this exercise, so it's a PR by default

    # workout volume calculation (v = sets * reps * weight)
    volume = workout.sets * workout.reps * workout.weight

    new_workout = {
        "id": next_id,
        "exercise_name": workout.exercise_name,
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
            workout["exercise_name"] = updated_workout.exercise_name
            workout["sets"] = updated_workout.sets
            workout["reps"] = updated_workout.reps
            workout["weight"] = updated_workout.weight
            # Recalculate volume
            workout["volume"] = workout["sets"] * workout["reps"] * workout["weight"]
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
