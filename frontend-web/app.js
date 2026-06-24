// 1. SET YOUR LIVE RAILWAY URL HERE
const BACKEND_URL = "https://smart-garden-advisory-system-production.up.railway.app/";

// DOM Elements
const tempVal = document.getElementById('temp-val');
const humidityVal = document.getElementById('humidity-val');
const rainVal = document.getElementById('rain-val');
const weatherLoading = document.getElementById('weather-loading');
const weatherData = document.getElementById('weather-data');

const plantIdInput = document.getElementById('plant-id-input');
const checkStatusBtn = document.getElementById('check-status-btn');
const plantLoading = document.getElementById('plant-loading');
const plantData = document.getElementById('plant-data');
const moistureVal = document.getElementById('moisture-val');
const thresholdVal = document.getElementById('threshold-val');
const wateringStatus = document.getElementById('watering-status');
const recommendationVal = document.getElementById('recommendation-val');

const manualWaterForm = document.getElementById('manual-water-form');
const actionPlantId = document.getElementById('action-plant-id');
const waterAmount = document.getElementById('water-amount');
const formFeedback = document.getElementById('form-feedback');

// --- FETCH WEATHER DATA ---
async function fetchWeather() {
    try {
        const response = await fetch(`${BACKEND_URL}/test-weather`);
        if (!response.ok) throw new Error('Network response error');

        const data = await response.json();

        tempVal.textContent = data.temperature_f;
        humidityVal.textContent = data.humidity_percent;
        rainVal.textContent = data.current_rain_mm;

        weatherLoading.classList.add('hidden');
        weatherData.classList.remove('hidden');
    } catch (error) {
        console.error("Error fetching weather:", error);
        weatherLoading.textContent = "❌ Failed to load weather data.";
    }
}

// --- FETCH PLANT HEALTH STATUS ---
async function fetchPlantStatus(plantId) {
    plantLoading.classList.remove('hidden');
    plantData.classList.add('hidden');

    try {
        const response = await fetch(`${BACKEND_URL}/check-watering-need/${plantId}`);
        if (!response.ok) throw new Error('Plant data fetch failed');

        const data = await response.json();

        moistureVal.textContent = data.current_moisture;
        thresholdVal.textContent = data.target_threshold;
        recommendationVal.textContent = data.recommended_amount;

        // Handle badge styling based on requirement
        if (data.watering_required) {
            wateringStatus.textContent = "YES";
            wateringStatus.className = "badge danger";
        } else {
            wateringStatus.textContent = "NO";
            wateringStatus.className = "badge success";
        }

        plantLoading.classList.add('hidden');
        plantData.classList.remove('hidden');
    } catch (error) {
        console.error("Error fetching plant status:", error);
        plantLoading.textContent = `❌ Plant ID ${plantId} not found or error loading data.`;
    }
}

// --- SUBMIT MANUAL WATERING LOG (POST) ---
manualWaterForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    formFeedback.textContent = "Submitting log...";
    formFeedback.style.color = "var(--text-main)";

    const payload = {
        plant_id: parseInt(actionPlantId.value),
        amount: waterAmount.value
    };

    try {
        const response = await fetch(`${BACKEND_URL}/manual-watering`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            formFeedback.textContent = `✅ Success: ${data.message}`;
            formFeedback.style.color = "var(--accent-green)";
            // Refresh plant data automatically if it matches the current viewed plant
            if (payload.plant_id === parseInt(plantIdInput.value)) {
                fetchPlantStatus(payload.plant_id);
            }
        } else {
            formFeedback.textContent = `❌ Error: ${data.message}`;
            formFeedback.style.color = "var(--alert-red)";
        }
    } catch (error) {
        console.error("Error logging manual watering:", error);
        formFeedback.textContent = "❌ Failed to reach the cloud server.";
        formFeedback.style.color = "var(--alert-red)";
    }
});

// Event Listeners for Buttons
checkStatusBtn.addEventListener('click', () => {
    const id = plantIdInput.value.trim();
    if (id) fetchPlantStatus(id);
});

// Initial Load Actions
window.addEventListener('DOMContentLoaded', () => {
    fetchWeather();
    fetchPlantStatus(1); // Load default plant id 1 on startup
});