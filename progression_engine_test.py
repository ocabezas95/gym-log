import pytest
from progression_engine import ProgressionEngine


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

BENCH_PRESS = {
    "id": 1,
    "name": "Barbell Bench Press",
    "muscle_group": "Chest",
    "equipment": "Barbell",
    "difficulty": "Intermediate",
    "rep_range": [8, 12],
}

SQUAT = {
    "id": 2,
    "name": "Back Squat",
    "muscle_group": "Legs",
    "equipment": "Barbell",
    "difficulty": "Advanced",
    "rep_range": [4, 8],
}

DUMBBELL_FLY = {
    "id": 3,
    "name": "Dumbbell Fly",
    "muscle_group": "Chest",
    "equipment": "Dumbbell",
    "difficulty": "Intermediate",
    "rep_range": [10, 15],
}

PUSH_UP = {
    "id": 4,
    "name": "Push-Up",
    "muscle_group": "Chest",
    "equipment": "Bodyweight",
    "difficulty": "Beginner",
    "rep_range": [10, 15],
}

CALF_RAISE = {
    "id": 5,
    "name": "Standing Calf Raise",
    "muscle_group": "Calves",
    "equipment": "Machine",
    "difficulty": "Beginner",
    "rep_range": [12, 20],
}

EXERCISE_NO_REP_RANGE = {
    "id": 6,
    "name": "Old Exercise",
    "muscle_group": "Chest",
    "equipment": "Barbell",
    "difficulty": "Intermediate",
    # intentionally no rep_range
}


@pytest.fixture
def engine():
    return ProgressionEngine([
        BENCH_PRESS, SQUAT, DUMBBELL_FLY, PUSH_UP, CALF_RAISE,
        EXERCISE_NO_REP_RANGE,
    ])


def bench_workout(sets, rep_range=None):
    """Helper: build a workout dict for bench press."""
    return {
        "exercise_id": 1,
        "sets": sets,
        "rep_range": rep_range,
    }


def squat_workout(sets, rep_range=None):
    return {
        "exercise_id": 2,
        "sets": sets,
        "rep_range": rep_range,
    }


# ---------------------------------------------------------------------------
# Rule 1 — Rep-cap trigger
# ---------------------------------------------------------------------------

def test_flag_fires_all_sets_at_cap_rir_lte_2(engine):
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 2},
        {"reps": 12, "weight": 135.0, "rir": 1},
        {"reps": 12, "weight": 135.0, "rir": 0},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True


def test_flag_fires_at_rir_boundary(engine):
    """RIR exactly 2 should still fire (inclusive ≤ 2)."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 2},
        {"reps": 12, "weight": 135.0, "rir": 2},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True


def test_flag_fires_without_rir_logged(engine):
    """All sets at rep cap, no RIR — flag should fire (RIR not required)."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0},
        {"reps": 12, "weight": 135.0},
        {"reps": 12, "weight": 135.0},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True


def test_flag_fires_mixed_rir_and_no_rir(engine):
    """Some sets have RIR ≤ 2, others have no RIR — flag should fire."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 1},
        {"reps": 12, "weight": 135.0},           # no RIR
        {"reps": 12, "weight": 135.0, "rir": 2},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True


def test_flag_suppressed_partial_sets(engine):
    """One set below rep cap — flag must NOT fire."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 1},
        {"reps": 10, "weight": 135.0, "rir": 1},  # below cap
        {"reps": 12, "weight": 135.0, "rir": 1},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is False


def test_flag_suppressed_high_rir(engine):
    """All sets at rep cap but one has RIR = 3 — flag must NOT fire."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 1},
        {"reps": 12, "weight": 135.0, "rir": 3},  # too easy → suppress flag
        {"reps": 12, "weight": 135.0, "rir": 1},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is False


# ---------------------------------------------------------------------------
# Rule 2 — Weight increase calculation
# ---------------------------------------------------------------------------

def test_weight_increase_upper_body_barbell(engine):
    """Bench press (Chest / Barbell): +5 lb, rounded up to nearest 5 lb."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 1},
        {"reps": 12, "weight": 135.0, "rir": 1},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True
    assert result["suggested_weight"] == 140.0  # 135 + 5, already on 5 lb boundary


def test_weight_increase_lower_body_barbell(engine):
    """Squat (Legs / Barbell): +10 lb, rounded up to nearest 5 lb."""
    workout = squat_workout([
        {"reps": 8, "weight": 225.0, "rir": 1},
        {"reps": 8, "weight": 225.0, "rir": 1},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True
    assert result["suggested_weight"] == 235.0  # 225 + 10


def test_weight_increase_dumbbell_rounding(engine):
    """Dumbbell fly: +5 lb upper body, rounded to nearest 2.5 lb."""
    workout = {
        "exercise_id": 3,  # Dumbbell Fly
        "sets": [
            {"reps": 15, "weight": 37.5, "rir": 1},
            {"reps": 15, "weight": 37.5, "rir": 2},
        ],
    }
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True
    # 37.5 + 5 = 42.5 → ceil(42.5 / 2.5) * 2.5 = 17 * 2.5 = 42.5
    assert result["suggested_weight"] == 42.5


def test_weight_increase_uses_max_weight_across_sets(engine):
    """With mixed set weights, suggested_weight must be based on the max."""
    workout = bench_workout([
        {"reps": 12, "weight": 130.0, "rir": 1},
        {"reps": 12, "weight": 135.0, "rir": 1},  # max
        {"reps": 12, "weight": 125.0, "rir": 2},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True
    # max = 135, upper body +5, barbell increment 5 → 140
    assert result["suggested_weight"] == 140.0


# ---------------------------------------------------------------------------
# Rule 3 — RIR auto-regulation
# ---------------------------------------------------------------------------

def test_too_easy_alert_rir_gt_4(engine):
    """A set with RIR > 4 triggers a too_easy alert."""
    workout = bench_workout([
        {"reps": 10, "weight": 135.0, "rir": 5},
        {"reps": 10, "weight": 135.0, "rir": 2},
    ])
    result = engine.analyze(workout)
    alerts = result["rir_alerts"]
    assert any(a["type"] == "too_easy" for a in alerts)
    too_easy = next(a for a in alerts if a["type"] == "too_easy")
    assert too_easy["set_index"] == 0
    assert too_easy["suggested_weight"] is not None


def test_failure_alert_rir_0_before_min_reps(engine):
    """RIR 0 AND reps < rep_range[0] → failure alert with ~10% weight decrease."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 2},
        {"reps": 6, "weight": 135.0, "rir": 0},  # failed before min (8)
    ])
    result = engine.analyze(workout)
    alerts = result["rir_alerts"]
    assert any(a["type"] == "failure" for a in alerts)
    failure = next(a for a in alerts if a["type"] == "failure")
    assert failure["set_index"] == 1
    # 135 * 0.9 = 121.5 → round(121.5 / 5) * 5 = round(24.3) * 5 = 24 * 5 = 120
    assert failure["suggested_weight"] == 120.0


def test_no_alerts_when_rir_missing(engine):
    """Sets without rir logged → rir_alerts must be empty."""
    workout = bench_workout([
        {"reps": 10, "weight": 135.0},
        {"reps": 10, "weight": 135.0},
    ])
    result = engine.analyze(workout)
    assert result["rir_alerts"] == []


def test_bodyweight_returns_null_suggested_weight(engine):
    """Bodyweight exercise → suggested_weight is None everywhere."""
    workout = {
        "exercise_id": 4,  # Push-Up / Bodyweight
        "sets": [
            {"reps": 15, "weight": 0.0, "rir": 5},
            {"reps": 15, "weight": 0.0, "rir": 5},
        ],
    }
    result = engine.analyze(workout)
    assert result["suggested_weight"] is None
    for alert in result["rir_alerts"]:
        assert alert["suggested_weight"] is None


# ---------------------------------------------------------------------------
# Edge cases / None-return paths
# ---------------------------------------------------------------------------

def test_returns_none_missing_rep_range(engine):
    """No workout rep_range AND exercise has no default → returns None."""
    workout = {
        "exercise_id": 6,  # EXERCISE_NO_REP_RANGE
        "sets": [
            {"reps": 10, "weight": 135.0, "rir": 1},
        ],
    }
    result = engine.analyze(workout)
    assert result is None


def test_returns_none_exercise_not_found(engine):
    """exercise_id not in engine → returns None."""
    workout = {
        "exercise_id": 9999,
        "sets": [
            {"reps": 10, "weight": 135.0, "rir": 1},
        ],
    }
    result = engine.analyze(workout)
    assert result is None


def test_workout_override_takes_precedence(engine):
    """Workout-level rep_range overrides exercise default."""
    # Bench press default is [8, 12]; override to [5, 8]
    workout = bench_workout(
        sets=[
            {"reps": 8, "weight": 155.0, "rir": 1},
            {"reps": 8, "weight": 155.0, "rir": 2},
        ],
        rep_range=[5, 8],
    )
    result = engine.analyze(workout)
    # Should flag because reps==8==override_cap and all RIR ≤ 2
    assert result["flag_for_increase"] is True


def test_calves_classified_as_lower_body(engine):
    """Calf raise (Calves / Machine) → lower body → +10 lb increase."""
    workout = {
        "exercise_id": 5,  # Calf Raise / Calves / Machine
        "sets": [
            {"reps": 20, "weight": 100.0, "rir": 1},
            {"reps": 20, "weight": 100.0, "rir": 2},
        ],
    }
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True
    # 100 + 10 = 110, machine increment 5 → 110
    assert result["suggested_weight"] == 110.0


# ---------------------------------------------------------------------------
# Response structure — reason field
# ---------------------------------------------------------------------------

def test_reason_non_null_only_when_flag_true(engine):
    """reason field must be None when flag_for_increase is False."""
    workout = bench_workout([
        {"reps": 10, "weight": 135.0, "rir": 1},  # not at rep cap (12)
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is False
    assert result["reason"] is None


def test_reason_present_when_flag_true(engine):
    """reason must be a non-empty string when flag_for_increase is True."""
    workout = bench_workout([
        {"reps": 12, "weight": 135.0, "rir": 1},
        {"reps": 12, "weight": 135.0, "rir": 1},
    ])
    result = engine.analyze(workout)
    assert result["flag_for_increase"] is True
    assert isinstance(result["reason"], str)
    assert len(result["reason"]) > 0
