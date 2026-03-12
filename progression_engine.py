import math

LOWER_BODY_GROUPS = {"Legs", "Calves"}

EQUIPMENT_INCREMENTS = {
    "Barbell": 5.0,
    "Dumbbell": 2.5,
    "Cable": 5.0,
    "Machine": 5.0,
    "Kettlebell": 8.0,
    "Bodyweight": None,
    "Other": 5.0,
}


class ProgressionEngine:
    def __init__(self, exercises: list[dict]):
        self._exercises = {e["id"]: e for e in exercises}

    def analyze(self, workout: dict) -> dict | None:
        """
        Returns progression analysis for a completed workout.

        Returns None if:
        - workout has no sets array (legacy flat schema)
        - exercise_id not found in the exercise index
        - no rep_range resolvable (neither on workout nor on exercise)
        """
        sets = workout.get("sets")
        if not isinstance(sets, list):
            return None

        exercise_id = workout.get("exercise_id")
        exercise = self._exercises.get(exercise_id)
        if exercise is None:
            return None

        rep_range = workout.get("rep_range") or exercise.get("rep_range")
        if rep_range is None or len(rep_range) < 2:
            return None

        min_reps, max_reps = rep_range[0], rep_range[1]
        max_weight = max((s.get("weight", 0.0) for s in sets), default=0.0)

        flag_for_increase, reason = self._check_rep_cap(sets, max_reps, max_weight, exercise)
        rir_alerts = self._check_rir_alerts(sets, min_reps, exercise)

        return {
            "flag_for_increase": flag_for_increase,
            "suggested_weight": self._suggested_increase(exercise, max_weight) if flag_for_increase else None,
            "reason": reason,
            "rir_alerts": rir_alerts,
        }

    def _check_rep_cap(
        self, sets: list[dict], max_reps: int, max_weight: float, exercise: dict
    ) -> tuple[bool, str | None]:
        """Rule 1: all sets at rep cap, all logged RIR ≤ 2."""
        if not all(s.get("reps") == max_reps for s in sets):
            return False, None

        for s in sets:
            rir = s.get("rir")
            if rir is not None and rir > 2:
                return False, None

        n = len(sets)
        reason = f"All {n} set{'s' if n != 1 else ''} completed at top of rep range ({max_reps} reps)"
        return True, reason

    def _check_rir_alerts(
        self, sets: list[dict], min_reps: int, exercise: dict
    ) -> list[dict]:
        """Rule 3: per-set RIR auto-regulation alerts."""
        alerts = []
        for i, s in enumerate(sets):
            rir = s.get("rir")
            if rir is None:
                continue

            weight = s.get("weight", 0.0)
            reps = s.get("reps", 0)

            if rir > 4:
                alerts.append({
                    "set_index": i,
                    "type": "too_easy",
                    "message": (
                        f"Set {i + 1}: RIR {rir} is too easy — "
                        "consider increasing weight for the next set"
                        if exercise.get("equipment") != "Bodyweight"
                        else f"Set {i + 1}: RIR {rir} is too easy — "
                        "consider a harder variation or added resistance"
                    ),
                    "suggested_weight": self._suggested_increase(exercise, weight),
                })
            elif rir == 0 and reps < min_reps:
                suggested = self._failure_decrease(exercise, weight)
                alerts.append({
                    "set_index": i,
                    "type": "failure",
                    "message": (
                        f"Set {i + 1}: Failed before minimum reps ({reps}/{min_reps}) "
                        "— decrease weight by ~10% next session"
                    ),
                    "suggested_weight": suggested,
                })

        return alerts

    def _suggested_increase(self, exercise: dict, current_weight: float) -> float | None:
        """
        Computes the suggested next weight given a starting weight.
        `current_weight` is caller-supplied — callers decide whether to pass
        the workout-max weight (Rule 2) or an individual set's weight (Rule 3).
        Returns None for Bodyweight exercises.
        """
        muscle_group = exercise.get("muscle_group", "")
        equipment = exercise.get("equipment", "Other")

        increase = 10.0 if muscle_group in LOWER_BODY_GROUPS else 5.0
        increment = EQUIPMENT_INCREMENTS.get(equipment, 5.0)

        if increment is None:
            return None

        raw = current_weight + increase
        return math.ceil(raw / increment) * increment

    def _failure_decrease(self, exercise: dict, current_weight: float) -> float | None:
        equipment = exercise.get("equipment", "Other")
        increment = EQUIPMENT_INCREMENTS.get(equipment, 5.0)

        if increment is None:
            return None

        raw = current_weight * 0.9
        return round(raw / increment) * increment
