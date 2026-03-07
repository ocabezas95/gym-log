import json
import os
from datetime import datetime

# workout menu
def workout_menu():
    print("Workout Menu")
    print("1. Add Exercise")
    print("2. View Exercises")
    print("3. Delete Exercise")
    print("4. Exit")

# functions to load and save workouts
def load_workouts():
    if not os.path.exists('workouts.json'):
        return []
    with open('workouts.json', 'r') as file:
        return json.load(file)


def save_workouts(workouts):
    with open('workouts.json', 'w') as file:
        json.dump(workouts, file, indent=4)


# main program loop
while True:
    workout_menu()
    user_input = input("Enter your choice: ")

    if user_input == "1":
        exercise_name = input('Enter exercise name: ')
        sets = int(input('Enter number of sets: '))
        reps = int(input('Enter number of reps: '))
        weight = float(input('Enter weight used: '))
        today = datetime.today().isoformat()

        workouts = load_workouts()
        if workouts:
            next_id = max(w["id"] for w in workouts) + 1
        else:
            next_id = 1

        new_workout = {
            "id": next_id,
            "exercise_name": exercise_name,
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "date": today
        }

        workouts.append(new_workout)
        save_workouts(workouts)
        print("Exercise added successfully!")

    elif user_input == "2":
        workouts = load_workouts()
        if not workouts:
            print("No exercises found.")
        else:
            for workout in workouts:
                print(
                    f"Exercise: {workout['exercise_name']}, Sets: {workout['sets']}, Reps: {workout['reps']}, Weight: {workout['weight']}, Date: {workout['date']}")

    elif user_input == "3":
        workouts = load_workouts()
        if not workouts:
            print("No exercises found.")
            continue
        for w in workouts:
            print(f"ID: {w['id']} - {w['exercise_name']}")

        try:
            delete_id = int(input('Enter the ID of the exercise to delete: '))
        except ValueError:
            print("Invalid ID.")
            continue

        original_length = len(workouts)
        workouts = [w for w in workouts if w['id'] != delete_id]

        if len(workouts) < original_length:
            save_workouts(workouts)
            print("Exercise deleted successfully!")
        else:
            print("Exercise not found.")

    elif user_input == "4":
        print("Exiting the program. Goodbye!")
        break

    else:
        print("Invalid choice. Please try again.")
