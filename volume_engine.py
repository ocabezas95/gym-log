from datetime import datetime, timedelta
from collections import defaultdict


class HybridVolumeEngine:

    def __init__(self, workouts, exercises):
        self.workouts = workouts
        self.exercise_map = {
            e["id"]: e["muscle_group"] for e in exercises
        }
    
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
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
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
                percent_change[muscle] = ((current_volume[muscle] - prev) / prev) * 100
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

        acwr = (acute_avg / chronic_avg) if chronic_avg > 0 else 0

        return {
            "acute_avg": acute_avg,
            "chronic_avg": chronic_avg,
            "acwr": acwr
        }
    
    # Trainer Insights
    def trainer_insights(self):
        week_data = self.calendar_week_volume()
        current = week_data["current_week"]

        if not current:
            return {}

        if len(current) < 2:
            imbalance = None  # Not enough data for imbalance
        else:
            max_muscle = max(current, key=current.get)
            min_muscle = min(current, key=current.get)

            imbalance = {
                "dominant_muscle": max_muscle,
                "weakest_muscle": min_muscle
            }

        rolling = self.rolling_window_volume()
        warning = rolling["acwr"] > 1.5

        return {
            "muscle_imbalance": imbalance,
            "overtraining_warning": warning,
            "acwr": rolling["acwr"]
        }
    
    # Master Stats
    def generate_stats(self):
        return {
            "calendar_week": self.calendar_week_volume(),
            "rolling_window": self.rolling_window_volume(),
            "trainer_insights": self.trainer_insights()
        }
    
  


                
