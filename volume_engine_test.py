import pytest
from datetime import datetime, timedelta
from volume_engine import HybridVolumeEngine


@pytest.fixture
def exercises():
    """Sample exercises with muscle groups"""
    return [
        {"id": 1, "name": "Bench Press", "muscle_group": "Chest"},
        {"id": 2, "name": "Squats", "muscle_group": "Legs"},
        {"id": 3, "name": "Deadlifts", "muscle_group": "Back"},
    ]


@pytest.fixture
def sample_workouts():
    """Sample workouts for testing"""
    now = datetime.now()
    return [
        {
            "date": (now - timedelta(days=10)).isoformat(),
            "exercise_id": 1,
            "sets": [
                {"reps": 8, "weight": 185},
                {"reps": 8, "weight": 185},
                {"reps": 8, "weight": 185},
            ]
        },
        {
            "date": (now - timedelta(days=5)).isoformat(),
            "exercise_id": 1,
            "sets": [
                {"reps": 10, "weight": 195},
                {"reps": 10, "weight": 195},
                {"reps": 10, "weight": 195},
            ]
        },
        {
            "date": (now - timedelta(days=2)).isoformat(),
            "exercise_id": 2,
            "sets": [
                {"reps": 6, "weight": 225},
                {"reps": 6, "weight": 225},
            ]
        },
        {
            "date": (now - timedelta(days=1)).isoformat(),
            "exercise_id": 1,
            "sets": [
                {"reps": 12, "weight": 185},
                {"reps": 12, "weight": 185},
            ]
        },
    ]


class TestHybridVolumeEngine:

    def test_calculate_total_volume_basic(self, exercises, sample_workouts):
        """Test basic volume calculation per muscle group"""
        engine = HybridVolumeEngine(sample_workouts, exercises)
        volume = engine.calculate_total_volume(sample_workouts)

        # Chest: (8*185)*3 + (10*195)*3 + (12*185)*2 = 4440 + 5850 + 4440 = 14730
        # Legs: (6*225)*2 = 2700
        assert volume["Chest"] == 14730
        assert volume["Legs"] == 2700
        assert "Back" not in volume  # No workouts for Back

    def test_calculate_total_volume_empty(self, exercises):
        """Test volume calculation with no workouts"""
        engine = HybridVolumeEngine([], exercises)
        volume = engine.calculate_total_volume([])

        assert volume == {}

    def test_calculate_total_volume_unknown_exercise(self, exercises, sample_workouts):
        """Test that unknown exercise IDs are skipped"""
        unknown_workout = {
            "date": datetime.now().isoformat(),
            "exercise_id": 999,
            "sets": [{"reps": 10, "weight": 100}]
        }
        workouts = sample_workouts + [unknown_workout]
        engine = HybridVolumeEngine(workouts, exercises)
        volume = engine.calculate_total_volume(workouts)

        # Should only calculate for known exercises
        assert "Chest" in volume
        assert "Legs" in volume

    def test_calendar_week_volume_structure(self, exercises, sample_workouts):
        """Test calendar week volume returns correct structure"""
        engine = HybridVolumeEngine(sample_workouts, exercises)
        result = engine.calendar_week_volume()

        assert "current_week" in result
        assert "last_week" in result
        assert "percent_change" in result
        assert isinstance(result["current_week"], dict)
        assert isinstance(result["last_week"], dict)
        assert isinstance(result["percent_change"], dict)

    def test_rolling_window_volume_structure(self, exercises, sample_workouts):
        """Test rolling window volume returns correct structure"""
        engine = HybridVolumeEngine(sample_workouts, exercises)
        result = engine.rolling_window_volume()

        assert "acute_avg" in result
        assert "chronic_avg" in result
        assert "acwr" in result
        assert result["acute_avg"] >= 0
        assert result["chronic_avg"] >= 0
        assert result["acwr"] >= 0

    def test_rolling_window_acwr_calculation(self, exercises):
        """Test ACWR calculation with known values"""
        now = datetime.now()
        # High volume in last 7 days, low volume before
        workouts = [
            # Low volume 28-7 days ago
            {
                "date": (now - timedelta(days=20)).isoformat(),
                "exercise_id": 1,
                "sets": [{"reps": 5, "weight": 100}]
            },
            # High volume last 7 days
            {
                "date": (now - timedelta(days=2)).isoformat(),
                "exercise_id": 1,
                "sets": [{"reps": 10, "weight": 200}, {"reps": 10, "weight": 200}]
            },
        ]

        engine = HybridVolumeEngine(workouts, exercises)
        result = engine.rolling_window_volume()

        # ACWR should be positive
        assert result["acwr"] > 0
        assert result["acute_avg"] > 0

    def test_trainer_insights_structure(self, exercises, sample_workouts):
        """Test trainer insights returns correct structure"""
        engine = HybridVolumeEngine(sample_workouts, exercises)
        result = engine.trainer_insights()

        if result:  # If there's data
            assert "muscle_imbalance" in result
            assert "overtraining_warning" in result
            assert "acwr" in result
            assert isinstance(result["muscle_imbalance"], dict)
            assert isinstance(result["overtraining_warning"], bool)

    def test_trainer_insights_muscle_imbalance(self, exercises):
        """Test muscle imbalance detection"""
        now = datetime.now()
        # High volume for Chest, low for Legs this week
        workouts = [
            {
                "date": (now - timedelta(days=2)).isoformat(),
                "exercise_id": 1,
                "sets": [{"reps": 10, "weight": 300} for _ in range(5)]
            },
            {
                "date": (now - timedelta(days=1)).isoformat(),
                "exercise_id": 2,
                "sets": [{"reps": 5, "weight": 100}]
            },
        ]

        engine = HybridVolumeEngine(workouts, exercises)
        insights = engine.trainer_insights()

        if insights:
            assert insights["muscle_imbalance"]["dominant_muscle"] == "Chest"
            assert insights["muscle_imbalance"]["weakest_muscle"] == "Legs"

    def test_generate_stats_complete(self, exercises, sample_workouts):
        """Test complete stats generation"""
        engine = HybridVolumeEngine(sample_workouts, exercises)
        stats = engine.generate_stats()

        assert "calendar_week" in stats
        assert "rolling_window" in stats
        assert "trainer_insights" in stats
        assert isinstance(stats["calendar_week"], dict)
        assert isinstance(stats["rolling_window"], dict)
        assert isinstance(stats["trainer_insights"], dict)

    def test_overtraining_warning(self, exercises):
        """Test overtraining warning when ACWR > 1.5"""
        now = datetime.now()
        # Build a spike scenario: low baseline, then massive spike
        workouts = []

        # Low baseline (8-28 days ago)
        for i in range(8, 29):
            workouts.append({
                "date": (now - timedelta(days=i)).isoformat(),
                "exercise_id": 1,
                "sets": [{"reps": 8, "weight": 95} for _ in range(3)]
            })

        # Massive spike (last 7 days)
        for i in range(0, 7):
            workouts.append({
                "date": (now - timedelta(days=i)).isoformat(),
                "exercise_id": 1,
                "sets": [{"reps": 10, "weight": 315} for _ in range(5)]
            })

        engine = HybridVolumeEngine(workouts, exercises)
        insights = engine.trainer_insights()

        # Should trigger overtraining warning
        assert insights["overtraining_warning"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
