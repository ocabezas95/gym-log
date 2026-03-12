from datetime import datetime, timedelta
from collections import defaultdict


class HybridVolumeEngine:

    def __init__(self, workouts, exercises):
        self.workouts = workouts
        self.exercise_map = {
            e["id"]: e["muscle_group"] for e in exercises
        }

    # Stress Zone helper - not core but useful for insights
    # For UI if its 0.8 to 1.5 its green, below 0.8 yellow, above 1.5 red
    def _stress_zone(self, acwr):
        if acwr < 0.8:
            return "Undertraining"
        elif 0.8 <= acwr <= 1.3:
            return "green"
        elif 1.3 < acwr <= 1.5:
            return "yellow"
        else:
            return "red"

      # helper method to enrich workout data with exercise details
    def _normalize_sets(self, workout):
        """
        Ensures workout has set-array structure. Supports both flat and array schemas.
        """
        # Already correct schema
        if isinstance(workout.get("sets"), list):
            return workout["sets"]

        # Flat schema -> convert to array
        if isinstance(workout.get("sets"), int):
            return [{"reps": workout["reps"], "weight": workout["weight"]}
                    for _ in range(workout["sets"])
                    ]

        return []

    # Core volume calculation method

    def calculate_total_volume(self, logs):
        volume_by_muscle = defaultdict(float)

        for workout in logs:
            muscle = self.exercise_map.get(workout["exercise_id"])
            if not muscle:
                continue  # Skip if exercise ID not found

            normalize_sets = self._normalize_sets(workout)

            for s in normalize_sets:
                volume_by_muscle[muscle] += s["reps"] * s["weight"]

        return dict(volume_by_muscle)

    # Calendar week logic
    def calendar_week_volume(self):
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())  # Monday
        start_of_week = start_of_week.replace(
            hour=0, minute=0, second=0, microsecond=0)
        start_last_week = start_of_week - timedelta(days=7)
        end_last_week = start_of_week

        current_logs = []
        last_logs = []

        for w in self.workouts:
            w_date = datetime.fromisoformat(w["date"])
            if start_of_week <= w_date <= now:
                current_logs.append(w)
            elif start_last_week <= w_date < end_last_week:
                last_logs.append(w)

        current_volume = self.calculate_total_volume(current_logs)
        last_volume = self.calculate_total_volume(last_logs)

        percent_change = {}

        for muscle in current_volume:
            prev = last_volume.get(muscle, 0)
            if prev > 0:
                percent_change[muscle] = (
                    (current_volume[muscle] - prev) / prev) * 100
            else:
                percent_change[muscle] = None  # No previous data

        return {
            "current_week": current_volume,
            "last_week": last_volume,
            "percent_change": percent_change
        }

    # Rolling Window logic + ACWR
    def rolling_window_volume(self):
        now = datetime.now()
        last_7 = now - timedelta(days=7)
        last_28 = now - timedelta(days=28)

        acute_logs = []
        chronic_logs = []

        for w in self.workouts:
            w_date = datetime.fromisoformat(w["date"])
            if last_7 <= w_date <= now:
                acute_logs.append(w)
            if last_28 <= w_date < now:
                chronic_logs.append(w)

        # Global volume
        acute_volume = sum(
            sum(s["reps"] * s["weight"] for s in self._normalize_sets(w))
            for w in acute_logs
        )

        chronic_volume = sum(
            sum(s["reps"] * s["weight"] for s in self._normalize_sets(w))
            for w in chronic_logs
        )

        acute_avg = acute_volume / 7 if acute_logs else 0
        chronic_avg = chronic_volume / 28 if chronic_logs else 0

        global_acwr = (acute_avg / chronic_avg) if chronic_avg > 0 else 0

        # Per muscle group ACWR
        acute_by_muscle = defaultdict(float)
        chronic_by_muscle = defaultdict(float)

        for w in acute_logs:
            muscle = self.exercise_map.get(w["exercise_id"])
            if not muscle:
                continue

            for s in self._normalize_sets(w):
                acute_by_muscle[muscle] += s["reps"] * s["weight"]

        for w in chronic_logs:
            muscle = self.exercise_map.get(w["exercise_id"])
            if not muscle:
                continue

            for s in self._normalize_sets(w):
                chronic_by_muscle[muscle] += s["reps"] * s["weight"]

        muscle_acwr = {}

        for muscle in acute_by_muscle:
            acute_m = acute_by_muscle[muscle] / 7  # Daily average
            chronic_m = chronic_by_muscle.get(muscle, 0) / 28
            acwr = (acute_m / chronic_m) if chronic_m > 0 else 0

            muscle_acwr[muscle] = {
                "acute_avg": acute_m,
                "chronic_avg": chronic_m,
                "acwr": acwr,
                "stress_zone": self._stress_zone(acwr)
            }

        return {
            "global": {
                "acute_avg": acute_avg,
                "chronic_avg": chronic_avg,
                "acwr": global_acwr,
                "stress_zone": self._stress_zone(global_acwr)
            },
            "by_muscle": muscle_acwr
        }

    # Weekly hard sets metrics
    def weekly_sets_per_muscle(self):
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())  # Monday
        start_of_week = start_of_week.replace(
            hour=0, minute=0, second=0, microsecond=0)

        sets_by_muscle = defaultdict(int)

        for w in self.workouts:
            w_date = datetime.fromisoformat(w["date"])
            if start_of_week <= w_date <= now:
                muscle = self.exercise_map.get(w["exercise_id"])
                if not muscle:
                    continue

                normalize_sets = self._normalize_sets(w)
                sets_by_muscle[muscle] += len(normalize_sets)

        return dict(sets_by_muscle)

    # Daily volume history for charts

    def daily_volume_history(self, days=90):
        now = datetime.now()
        start = now - timedelta(days=days)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Bucket workouts by local date
        daily_totals = defaultdict(float)
        daily_muscles = defaultdict(lambda: defaultdict(float))

        for w in self.workouts:
            w_date = datetime.fromisoformat(w["date"])
            if w_date < start:
                continue
            date_key = w_date.strftime("%Y-%m-%d")
            muscle = self.exercise_map.get(w["exercise_id"])
            for s in self._normalize_sets(w):
                vol = s["reps"] * s["weight"]
                daily_totals[date_key] += vol
                if muscle:
                    daily_muscles[date_key][muscle] += vol

        # Build ordered list for every day in range
        result = []
        for i in range(days + 1):
            d = start + timedelta(days=i)
            if d > now:
                break
            key = d.strftime("%Y-%m-%d")
            result.append({
                "date": key,
                "total_volume": daily_totals.get(key, 0),
                "by_muscle": dict(daily_muscles[key]) if key in daily_muscles else {},
            })

        return result

    # Exercise weight progression over time
    def exercise_weight_history(self, exercise_id):
        sessions = defaultdict(
            lambda: {"max_weight": 0.0, "total_volume": 0.0})

        for w in self.workouts:
            if w["exercise_id"] != exercise_id:
                continue
            date_key = datetime.fromisoformat(w["date"]).strftime("%Y-%m-%d")
            for s in self._normalize_sets(w):
                vol = s["reps"] * s["weight"]
                sessions[date_key]["total_volume"] += vol
                if s["weight"] > sessions[date_key]["max_weight"]:
                    sessions[date_key]["max_weight"] = s["weight"]

        return [
            {"date": k, **v}
            for k, v in sorted(sessions.items())
        ]

    # Trainer Insights
    def trainer_insights(self):
        week_data = self.calendar_week_volume()
        current = week_data["current_week"]

        # muscle imbalance Logic - identifies if one muscle group is being trained significantly more than others
        if not current or len(current) < 2:
            imbalance = None  # Not enough data for imbalance
        else:
            max_muscle = max(current, key=current.get)
            min_muscle = min(current, key=current.get)

            imbalance = {
                "dominant_muscle": max_muscle,
                "weakest_muscle": min_muscle
            }

        # Global Fatigue Logic - uses rolling window ACWR to identify if user is at risk of overtraining
        rolling = self.rolling_window_volume()
        global_data = rolling["global"]

        acwr = global_data["acwr"]
        stress_zone = global_data["stress_zone"]

        # recommendation system based on ACWR
        if stress_zone == "green":
            recommendation = "Keep up the good work! Your training load is well balanced."
        elif stress_zone == "yellow":
            recommendation = "Caution: You're approaching a high training load. Consider adding more recovery or reducing volume slightly."
        elif stress_zone == "red":
            recommendation = "Warning: Your training load is very high. Prioritize recovery and consider reducing volume significantly to avoid overtraining."
        elif stress_zone == "Undertraining":
            recommendation = "Your training load is quite low. Consider increasing volume or intensity to make progress."
        else:
            recommendation = "No specific recommendation available."

        return {
            "muscle_imbalance": imbalance,
            "global_fatigue": {
                "acwr": acwr,
                "stress_zone": stress_zone,
                "recommendation": recommendation
            }
        }

    # Master Stats
    def generate_stats(self):
        return {
            "calendar_week": self.calendar_week_volume(),
            "rolling_window": self.rolling_window_volume(),
            "weekly_sets": self.weekly_sets_per_muscle(),
            "trainer_insights": self.trainer_insights()
        }
