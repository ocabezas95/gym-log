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

// === SET BUILDER ===

function createSetRow(container, reps = "", weight = "") {
    const idx = container.children.length + 1;
    const row = document.createElement("div");
    row.className = "set-row";
    row.innerHTML = `
        <span class="set-row-num">${idx}</span>
        <input type="number" class="set-reps" placeholder="Reps" min="1" value="${reps}" required>
        <input type="number" class="set-weight" placeholder="Lbs" step="0.1" min="0" value="${weight}" required>
        <button type="button" class="remove-set-btn" title="Remove set">&times;</button>`;
    row.querySelector(".remove-set-btn").addEventListener("click", () => {
        row.remove();
        renumberSets(container);
    });
    container.appendChild(row);
    return row;
}

function renumberSets(container) {
    container.querySelectorAll(".set-row").forEach((row, i) => {
        row.querySelector(".set-row-num").textContent = i + 1;
    });
}

function getSetsFromContainer(container) {
    return Array.from(container.querySelectorAll(".set-row")).map((row) => ({
        reps: Number(row.querySelector(".set-reps").value),
        weight: Number(row.querySelector(".set-weight").value),
    }));
}

function initSetBuilder(containerId, addBtnId) {
    const container = document.getElementById(containerId);
    const btn = document.getElementById(addBtnId);
    createSetRow(container);
    btn.addEventListener("click", () => createSetRow(container));
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

    const totalVolume = workouts.reduce((sum, w) => {
        if (w.volume != null) return sum + w.volume;
        if (Array.isArray(w.sets)) return sum + w.sets.reduce((s, x) => s + x.reps * x.weight, 0);
        return sum + (w.sets || 0) * (w.reps || 0) * (w.weight || 0);
    }, 0);
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
                .map((w) => {
                    const setsArr = Array.isArray(w.sets) ? w.sets : [];
                    const vol = w.volume ?? setsArr.reduce((s, x) => s + x.reps * x.weight, 0);

                    const setBadges = setsArr.length
                        ? setsArr.map((s, i) => `<span class="badge">S${i + 1}: ${s.reps}&times;${s.weight}</span>`).join("")
                        : `<span class="badge">${w.sets} sets</span><span class="badge">${w.reps} reps</span><span class="badge">${w.weight} lbs</span>`;

                    const setsJson = escapeHtml(JSON.stringify(setsArr.length ? setsArr : [{ reps: w.reps, weight: w.weight }]));

                    return `
                <div class="workout-card">
                    <div>
                        <div class="workout-name">${escapeHtml(w.exercise_name || "Unknown exercise")}</div>
                        <div class="workout-meta">
                            ${setBadges}
                            <span class="badge volume-badge">⚡ ${Math.round(vol).toLocaleString()} vol</span>
                            ${w.is_pr ? '<span class="pr-badge">🏆 PR</span>' : ""}
                        </div>
                    </div>
                    <div class="card-actions">
                        <button class="edit-btn"
                            data-id="${w.id}"
                            data-exercise-id="${w.exercise_id}"
                            data-sets="${setsJson}">Edit</button>
                        <button class="delete-btn" data-id="${w.id}">Remove</button>
                    </div>
                </div>`;
                })
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
            sets: JSON.parse(btn.dataset.sets),
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

    const container = document.getElementById("edit-set-rows");
    container.innerHTML = "";
    const sets = workout.sets || [];
    sets.forEach((s) => createSetRow(container, s.reps, s.weight));
    if (!sets.length) createSetRow(container);

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

    const container = document.getElementById("set-rows");
    const payload = {
        exercise_id: Number(document.getElementById("exercise_id").value),
        sets: getSetsFromContainer(container),
    };

    try {
        const added = await addWorkout(payload);
        e.target.reset();
        container.innerHTML = "";
        createSetRow(container);
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
        sets: getSetsFromContainer(document.getElementById("edit-set-rows")),
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
    initSetBuilder("set-rows", "add-set-btn");
    document.getElementById("edit-add-set-btn").addEventListener("click", () => {
        createSetRow(document.getElementById("edit-set-rows"));
    });
    await Promise.all([fetchWorkouts(), fetchTodayVolume()]);
    initTabs();
}

// === TABS ===

function initTabs() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
}

function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
    document.querySelectorAll(".view-panel").forEach((p) => p.classList.toggle("active", p.id === `view-${tabName}`));
    if (tabName === "analytics") loadAnalytics();
}

// === ANALYTICS ORCHESTRATOR ===

let chartInstances = {};

function destroyChart(key) {
    if (chartInstances[key]) {
        chartInstances[key].destroy();
        delete chartInstances[key];
    }
}

async function loadAnalytics() {
    try {
        const [history, insights] = await Promise.all([
            fetch("/api/volume/history?days=28").then((r) => r.json()),
            fetch("/api/volume/insights").then((r) => r.json()),
        ]);
        const historyLong = await fetch("/api/volume/history?days=90").then((r) => r.json());

        renderVolumeTrend(history);
        renderMuscleBreakdown(insights.calendar_week?.current_week || {});
        renderACWRGauges(insights.rolling_window?.by_muscle || {});
        renderHeatmap(historyLong);
        setupExerciseProgressSelector();
    } catch (err) {
        console.error("Failed to load analytics:", err);
    }
}

// === CHART: Volume Trend (Bar) ===

function renderVolumeTrend(history) {
    destroyChart("volumeTrend");
    const ctx = document.getElementById("chart-volume-trend");
    if (!ctx) return;

    const labels = history.map((d) => {
        const dt = new Date(d.date + "T00:00:00");
        return dt.toLocaleDateString("en-US", { weekday: "short", day: "numeric" });
    });
    const data = history.map((d) => d.total_volume);

    chartInstances.volumeTrend = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Volume (lbs)",
                data,
                backgroundColor: "rgba(230, 57, 70, 0.6)",
                borderColor: "rgba(230, 57, 70, 1)",
                borderWidth: 1,
                borderRadius: 4,
                hoverBackgroundColor: "rgba(230, 57, 70, 0.85)",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (c) => `${Math.round(c.raw).toLocaleString()} lbs`,
                    },
                },
            },
            scales: {
                x: {
                    ticks: { color: "#666", font: { size: 10 }, maxRotation: 45 },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: "#666",
                        font: { size: 10 },
                        callback: (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v),
                    },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
            },
        },
    });
}

// === CHART: Muscle Breakdown (Doughnut) ===

const MUSCLE_COLORS = {
    Chest: "#e63946", Back: "#457b9d", Legs: "#2dc653", Shoulders: "#f59e0b",
    Biceps: "#8b5cf6", Triceps: "#ec4899", Abs: "#06b6d4", Calves: "#84cc16",
    Traps: "#f97316", Forearms: "#a78bfa",
};

function renderMuscleBreakdown(currentWeek) {
    destroyChart("muscleBreakdown");
    const ctx = document.getElementById("chart-muscle-breakdown");
    if (!ctx) return;

    const muscles = Object.keys(currentWeek);
    if (!muscles.length) {
        ctx.parentElement.innerHTML = '<p class="analytics-empty">No muscle data this week</p>';
        return;
    }

    const colors = muscles.map((m) => MUSCLE_COLORS[m] || "#666");

    chartInstances.muscleBreakdown = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: muscles,
            datasets: [{
                data: muscles.map((m) => Math.round(currentWeek[m])),
                backgroundColor: colors,
                borderColor: "#1a1a1a",
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#ccc", font: { size: 11 }, padding: 12, usePointStyle: true },
                },
                tooltip: {
                    callbacks: {
                        label: (c) => ` ${c.label}: ${c.raw.toLocaleString()} lbs`,
                    },
                },
            },
        },
    });
}

// === CHART: Exercise Progression (Line) ===

function setupExerciseProgressSelector() {
    const select = document.getElementById("progress-exercise-select");
    if (!select || !exercises.length) return;

    select.innerHTML = '<option value="">— Select exercise —</option>' +
        exercises.map((ex) => `<option value="${ex.id}">${escapeHtml(ex.name)}</option>`).join("");

    // Remove old listener by replacing node
    const fresh = select.cloneNode(true);
    select.parentNode.replaceChild(fresh, select);

    fresh.addEventListener("change", async () => {
        const id = Number(fresh.value);
        if (!id) return;
        try {
            const data = await fetch(`/api/volume/exercise/${id}/progress`).then((r) => r.json());
            renderExerciseProgress(data);
        } catch (err) {
            console.error("Failed to load exercise progress:", err);
        }
    });
}

function renderExerciseProgress(data) {
    destroyChart("exerciseProgress");
    const ctx = document.getElementById("chart-exercise-progress");
    if (!ctx) return;

    if (!data.length) {
        ctx.parentElement.innerHTML = '<p class="analytics-empty">No history for this exercise</p><canvas id="chart-exercise-progress"></canvas>';
        return;
    }

    const labels = data.map((d) => {
        const dt = new Date(d.date + "T00:00:00");
        return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    });

    chartInstances.exerciseProgress = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Max Weight (lbs)",
                    data: data.map((d) => d.max_weight),
                    borderColor: "#e63946",
                    backgroundColor: "rgba(230, 57, 70, 0.1)",
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: "#e63946",
                    fill: true,
                    tension: 0.3,
                    yAxisID: "y",
                },
                {
                    label: "Session Volume",
                    data: data.map((d) => d.total_volume),
                    borderColor: "#457b9d",
                    backgroundColor: "rgba(69, 123, 157, 0.1)",
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: "#457b9d",
                    fill: true,
                    tension: 0.3,
                    yAxisID: "y1",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    labels: { color: "#ccc", font: { size: 11 }, usePointStyle: true },
                },
            },
            scales: {
                x: {
                    ticks: { color: "#666", font: { size: 10 } },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y: {
                    position: "left",
                    title: { display: true, text: "Weight (lbs)", color: "#666", font: { size: 10 } },
                    ticks: { color: "#e63946", font: { size: 10 } },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y1: {
                    position: "right",
                    title: { display: true, text: "Volume", color: "#666", font: { size: 10 } },
                    ticks: {
                        color: "#457b9d",
                        font: { size: 10 },
                        callback: (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v),
                    },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

// === ACWR STRESS GAUGES ===

function renderACWRGauges(byMuscle) {
    const container = document.getElementById("acwr-gauges");
    if (!container) return;

    const muscles = Object.keys(byMuscle);
    if (!muscles.length) {
        container.innerHTML = '<p class="acwr-empty">Not enough data for workload analysis. Keep training!</p>';
        return;
    }

    container.innerHTML = muscles.map((muscle) => {
        const d = byMuscle[muscle];
        const acwr = d.acwr || 0;
        const zone = d.stress_zone || "Undertraining";

        let colorClass, zoneName;
        if (zone === "green") { colorClass = "green"; zoneName = "Optimal"; }
        else if (zone === "yellow") { colorClass = "yellow"; zoneName = "Caution"; }
        else if (zone === "red") { colorClass = "red"; zoneName = "High Risk"; }
        else { colorClass = "gray"; zoneName = "Low"; }

        // Clamp bar width: ACWR 0–2.5 maps to 0–100%
        const pct = Math.min(100, (acwr / 2.5) * 100);

        return `
            <div class="acwr-row">
                <span class="acwr-label">${escapeHtml(muscle)}</span>
                <div class="acwr-bar-track">
                    <div class="acwr-bar-fill acwr-bar-fill--${colorClass}" style="width:${pct}%"></div>
                </div>
                <span class="acwr-value">${acwr.toFixed(2)}</span>
                <span class="acwr-zone-tag acwr-zone-tag--${colorClass}">${zoneName}</span>
            </div>`;
    }).join("");
}

// === HEATMAP ===

function renderHeatmap(historyLong) {
    const grid = document.getElementById("heatmap-grid");
    if (!grid) return;

    // Build a volume lookup
    const volMap = {};
    let maxVol = 0;
    for (const d of historyLong) {
        volMap[d.date] = d.total_volume;
        if (d.total_volume > maxVol) maxVol = d.total_volume;
    }

    const today = new Date();
    const todayKey = localDateKey(today);

    // Go back 13 weeks (91 days) and align to Monday
    const start = new Date(today);
    start.setDate(start.getDate() - 90);
    // Align to Monday
    while (start.getDay() !== 1) start.setDate(start.getDate() - 1);

    const cells = [];
    const cursor = new Date(start);

    while (cursor <= today) {
        const key = localDateKey(cursor);
        const vol = volMap[key] || 0;
        let level = "";
        if (vol > 0 && maxVol > 0) {
            const ratio = vol / maxVol;
            if (ratio <= 0.25) level = "l1";
            else if (ratio <= 0.5) level = "l2";
            else if (ratio <= 0.75) level = "l3";
            else level = "l4";
        }
        const isToday = key === todayKey;
        const dt = new Date(cursor);
        const title = `${dt.toLocaleDateString("en-US", { month: "short", day: "numeric" })}: ${Math.round(vol).toLocaleString()} lbs`;
        cells.push(`<div class="heatmap-cell ${level ? "heatmap-cell--" + level : ""} ${isToday ? "heatmap-cell--today" : ""}" title="${escapeHtml(title)}"></div>`);
        cursor.setDate(cursor.getDate() + 1);
    }

    grid.innerHTML = cells.join("");
}

init();
