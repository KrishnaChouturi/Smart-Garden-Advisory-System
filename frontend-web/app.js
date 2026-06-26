const BACKEND_URL = "https://smart-garden-advisory-system-production.up.railway.app";

const tempVal = document.getElementById('temp-val');
const humidityVal = document.getElementById('humidity-val');
const rainVal = document.getElementById('rain-val');
const upcomingRainBox = document.getElementById('upcoming-rain-box');
const weatherLoading = document.getElementById('weather-loading');
const weatherData = document.getElementById('weather-data');

const plantLoading = document.getElementById('plant-loading');
const plantData = document.getElementById('plant-data');
const moistureVal = document.getElementById('moisture-val');
const targetThresholdInput = document.getElementById('target-threshold-input');
const computeBtn = document.getElementById('compute-btn');
const recommendationVal = document.getElementById('recommendation-val');

const manualWaterForm = document.getElementById('manual-water-form');
const waterAmount = document.getElementById('water-amount');
const formFeedback = document.getElementById('form-feedback');

async function fetchWeather() {
    try {
        const response = await fetch(`${BACKEND_URL}/test-weather`);
        if (!response.ok) throw new Error('Network response error');

        const data = await response.json();

        tempVal.textContent = data.temperature_f;
        humidityVal.textContent = data.humidity_percent;
        rainVal.textContent = data.current_rain_mm;

        if (data.upcoming_rain) {
            upcomingRainBox.innerHTML = `🌧️ Yes (Expect ${data.upcoming_rain_val}mm)`;
            upcomingRainBox.style.color = "#dc3545";
        } else {
            upcomingRainBox.innerHTML = `✅ None Expected`;
            upcomingRainBox.style.color = "#28a745";
        }

        weatherLoading.classList.add('hidden');
        weatherData.classList.remove('hidden');
    } catch (error) {
        console.error("Error fetching weather:", error);
        weatherLoading.textContent = "❌ Failed to load weather data.";
    }
}

async function fetchSoilTelemetry() {
    try {
        const response = await fetch(`${BACKEND_URL}/compute-recommendation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_threshold: targetThresholdInput.value })
        });
        const data = await response.json();

        if (response.ok) {
            moistureVal.textContent = data.current_moisture;
            plantLoading.classList.add('hidden');
            plantData.classList.remove('hidden');
        }
    } catch (error) {
        plantLoading.textContent = "❌ Failed to pull telemetry data rows.";
    }
}

computeBtn.addEventListener('click', async () => {
    computeBtn.textContent = "Calculating...";
    try {
        const response = await fetch(`${BACKEND_URL}/compute-recommendation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_threshold: parseInt(targetThresholdInput.value) })
        });
        const data = await response.json();

        if (response.ok) {
            recommendationVal.textContent = data.recommendation;
            alert(`Analysis complete! System recommends: ${data.recommendation}`);
        } else {
            alert(`Error running model: ${data.message}`);
        }
    } catch (err) {
        alert("Failed to reach processing cluster.");
    } finally {
        computeBtn.textContent = "Compute Smart Recommendation";
    }
});

manualWaterForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    formFeedback.textContent = "Submitting override context...";

    const selectedAmount = waterAmount.value;

    try {
        const response = await fetch(`${BACKEND_URL}/manual-watering`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: selectedAmount })
        });

        const data = await response.json();

        if (response.ok) {
            formFeedback.textContent = `✅ Successfully logged Override: ${selectedAmount}`;
            formFeedback.style.color = "#28a745";
            recommendationVal.textContent = selectedAmount;
        } else {
            formFeedback.textContent = `❌ Error: ${data.message}`;
            formFeedback.style.color = "#dc3545";
        }
    } catch (error) {
        formFeedback.textContent = "❌ Network connection dropped.";
        formFeedback.style.color = "#dc3545";
    }
});

window.addEventListener('DOMContentLoaded', () => {
    fetchWeather();
    fetchSoilTelemetry();
});