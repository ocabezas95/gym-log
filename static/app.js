/* ============================================================
   GYM LOG — app.js
   State → Helpers → API → Render → Events → Init
   ============================================================ */

// === STATE ===

const API_WORKOUTS = "/api/workouts";
const API_EXERCISES = "/api/exercises";

let exercises = [];

// === HELPERS ===

function localDateKey(d) {
    const date = d instanceof Date ? d : new Date(d);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

function calcStreak(workouts) {
    const dates = new Set(workouts.map((w) => (w.date || "").slice(0, 10)));
    let streak = 0;
    const today = new Date();

    for (let i = 0; i < 365; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const key = localDateKey(d);
        if (dates.has(key)) {
            streak += 1;
        } else {
            if (i === 0) continue; // no workout today yet — keep counting back
            break;
        }
    }

    return streak;
}

function formatDateLabel(dateKey) {
    const todayKey = localDateKey(new Date());
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayKey = localDateKey(yesterday);

    if (dateKey === todayKey) return `Today · ${formatShortDate(dateKey)}`;
    if (dateKey === yesterdayKey) return `Yesterday · ${formatShortDate(dateKey)}`;
    return formatShortDate(dateKey);
}

function formatShortDate(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
    });
}

function escapeHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function toVolumeLabel(value) {
    return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(Math.round(value));
}

// === API ===

async function fetchExercises() {
    const res = await fetch(API_EXERCISES);
    if (!res.ok) throw new Error(`Failed to load exercises: ${res.status}`);
    exercises = await res.json();
    populateExerciseSelects();
}

async function fetchWorkouts() {
    try {
        const res = await fetch(API_WORKOUTS);
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const workouts = await res.json();
        renderWorkouts(workouts);
        updateStats(workouts);
    } catch (err) {
        console.error("Failed to load workouts:", err);
        document.getElementById("workout-list").innerHTML = `
            <div class="empty-state">
                <span>⚠️</span>
                <p>Could not load workouts. Is the server running?</p>
            </div>`;
    }
}

async function fetchTodayVolume() {
    try {
        const res = await fetch("/api/volume/today");
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const { total_volume } = await res.json();
        document.getElementById("stat-today-vol").textContent = toVolumeLabel(total_volume);
    } catch (err) {
        console.error("Failed to fetch today volume:", err);
    }
}

async function addWorkout(payload) {
    const res = await fetch(API_WORKOUTS, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Add failed: ${res.status}`);
    return res.json();
}

async function updateWorkout(id, payload) {
    const res = await fetch(`${API_WORKOUTS}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Update failed: ${res.status}`);
    return res.json();
}

async function deleteWorkout(id) {
    try {
        const res = await fetch(`${API_WORKOUTS}/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
        await fetchWorkouts();
        await fetchTodayVolume();
    } catch (err) {
        console.error("Failed to delete workout:", err);
    }
}

// === RENDER ===

function populateExerciseSelects() {
    const options = exercises
        .map((ex) => `<option value="${ex.id}">${escapeHtml(ex.name)} (${escapeHtml(ex.muscle_group)})</option>`)
        .join("");

    document.getElementById("exercise_id").innerHTML = options;
    document.getElementById("edit-exercise").innerHTML = options;
}

function updateStats(workouts) {
    document.getElementById("stat-count").textContent = workouts.length;

    const totalVolume = workouts.reduce(
        (sum, w) => sum + (w.volume ?? w.sets * w.reps * w.weight),
        0,
    );
    document.getElementById("stat-volume").textContent = toVolumeLabel(totalVolume);

    const streak = calcStreak(workouts);
    document.getElementById("stat-streak").textContent = streak > 0 ? `🔥 ${streak}` : "0";
}

function renderWorkouts(workouts) {
    const list = document.getElementById("workout-list");

    if (!workouts.length) {
        list.innerHTML = `
            <div class="empty-state">
                <span>🏋️</span>
                <p>No workouts yet. Add your first one!</p>
            </div>`;
        return;
    }

    // Group workouts by date
    const groups = {};
    workouts.forEach((w) => {
        const key = (w.date || "").slice(0, 10);
        if (!groups[key]) groups[key] = [];
        groups[key].push(w);
    });

    const sortedKeys = Object.keys(groups).sort((a, b) => b.localeCompare(a));

    list.innerHTML = sortedKeys
        .map((dateKey) => {
            const entries = groups[dateKey]
                .slice()
                .sort((a, b) => b.id - a.id)
                .map((w) => `
                <div class="workout-card">
                    <div>
                        <div class="workout-name">${escapeHtml(w.exercise_name || "Unknown exercise")}</div>
                        <div class="workout-meta">
                            <span class="badge">${w.sets} sets</span>
                            <span class="badge">${w.reps} reps</span>
                            <span class="badge">${w.weight} lbs</span>
                            <span class="badge volume-badge">⚡ ${Math.round(w.volume ?? w.sets * w.reps * w.weight).toLocaleString()} vol</span>
                            ${w.is_pr ? '<span class="pr-badge">🏆 PR</span>' : ""}
                        </div>
                    </div>
                    <div class="card-actions">
                        <button class="edit-btn"
                            data-id="${w.id}"
                            data-exercise-id="${w.exercise_id}"
                            data-sets="${w.sets}"
                            data-reps="${w.reps}"
                            data-weight="${w.weight}">Edit</button>
                        <button class="delete-btn" data-id="${w.id}">Remove</button>
                    </div>
                </div>`)
                .join("");

            return `
                <div class="date-group">
                    <div class="date-label">${formatDateLabel(dateKey)}</div>
                    <div class="date-entries">${entries}</div>
                </div>`;
        })
        .join("");

    // Attach action listeners after DOM is updated
    list.querySelectorAll(".delete-btn").forEach((btn) => {
        btn.addEventListener("click", () => deleteWorkout(Number(btn.dataset.id)));
    });

    list.querySelectorAll(".edit-btn").forEach((btn) => {
        btn.addEventListener("click", () => openEditModal({
            id: Number(btn.dataset.id),
            exercise_id: Number(btn.dataset.exerciseId),
            sets: Number(btn.dataset.sets),
            reps: Number(btn.dataset.reps),
            weight: Number(btn.dataset.weight),
        }));
    });
}

function launchConfetti() {
    const colors = ["#e63946", "#ff6b6b", "#ff8fa3", "#c9184a", "#ffffff"];
    for (let i = 0; i < 90; i++) {
        const el = document.createElement("div");
        el.className = "confetti-piece";
        el.style.left = `${Math.random() * 100}vw`;
        el.style.top = "-10px";
        el.style.background = colors[Math.floor(Math.random() * colors.length)];
        el.style.width = `${6 + Math.random() * 6}px`;
        el.style.height = `${6 + Math.random() * 6}px`;
        el.style.borderRadius = Math.random() > 0.5 ? "50%" : "2px";
        const duration = 1.8 + Math.random() * 1.6;
        el.style.animationDuration = `${duration}s`;
        el.style.animationDelay = `${Math.random() * 0.6}s`;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), (duration + 0.6) * 1000 + 200);
    }
}

// === EVENTS ===

function openEditModal(workout) {
    document.getElementById("edit-id").value = workout.id;
    document.getElementById("edit-exercise").value = String(workout.exercise_id);
    document.getElementById("edit-sets").value = String(workout.sets);
    document.getElementById("edit-reps").value = String(workout.reps);
    document.getElementById("edit-weight").value = String(workout.weight);
    document.getElementById("edit-modal").classList.add("open");
    document.getElementById("edit-exercise").focus();
}

function closeEditModal() {
    document.getElementById("edit-modal").classList.remove("open");
}

document.getElementById("workout-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector(".submit-btn");
    btn.disabled = true;

    const payload = {
        exercise_id: Number(document.getElementById("exercise_id").value),
        sets: Number(document.getElementById("sets").value),
        reps: Number(document.getElementById("reps").value),
        weight: Number(document.getElementById("weight").value),
    };

    try {
        const added = await addWorkout(payload);
        e.target.reset();
        if (exercises.length) {
            document.getElementById("exercise_id").value = String(exercises[0].id);
        }
        await fetchWorkouts();
        await fetchTodayVolume();
        if (added.is_pr) launchConfetti();
    } catch (err) {
        console.error("Failed to add workout:", err);
    } finally {
        btn.disabled = false;
    }
});

document.getElementById("edit-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector(".modal-save-btn");
    btn.disabled = true;

    const id = Number(document.getElementById("edit-id").value);
    const payload = {
        exercise_id: Number(document.getElementById("edit-exercise").value),
        sets: Number(document.getElementById("edit-sets").value),
        reps: Number(document.getElementById("edit-reps").value),
        weight: Number(document.getElementById("edit-weight").value),
    };

    try {
        await updateWorkout(id, payload);
        closeEditModal();
        await fetchWorkouts();
        await fetchTodayVolume();
    } catch (err) {
        console.error("Failed to update workout:", err);
    } finally {
        btn.disabled = false;
    }
});

document.getElementById("modal-cancel").addEventListener("click", closeEditModal);

document.getElementById("edit-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeEditModal();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeEditModal();
});

// === INIT ===

async function init() {
    try {
        await fetchExercises();
    } catch (err) {
        console.error("Failed to load exercises:", err);
    }
    await Promise.all([fetchWorkouts(), fetchTodayVolume()]);
}

init();
