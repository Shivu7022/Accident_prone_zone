import { useEffect, useState, useCallback } from "react";
import "./WeatherCard.css";

const API_URL = "http://127.0.0.1:8001/api/weather";

export default function WeatherCard({ location, locationName, onWeatherUpdate }) {
  const hasLocation =
    Number.isFinite(location?.lat) && Number.isFinite(location?.lon);
  const latitude = hasLocation ? Number(Number(location.lat).toFixed(2)) : null;
  const longitude = hasLocation ? Number(Number(location.lon).toFixed(2)) : null;
  const locationKey = hasLocation ? `${latitude},${longitude}` : null;
  const [weatherResult, setWeatherResult] = useState({
    locationKey: null,
    weather: null,
    error: "",
  });
  const [refreshing, setRefreshing] = useState(false);
  const weather = weatherResult.locationKey === locationKey
    ? weatherResult.weather
    : null;
  const error = weatherResult.locationKey === locationKey
    ? weatherResult.error
    : "";
  const loading = hasLocation && !weather && !error;

  const fetchWeather = useCallback(async () => {
    if (!hasLocation) return;

    try {
      const response = await fetch(
        `${API_URL}?lat=${latitude}&lon=${longitude}`
      );

      if (!response.ok) {
        throw new Error(`Weather API returned ${response.status}`);
      }

      const data = await response.json();
      setWeatherResult({ locationKey, weather: data, error: "" });
      onWeatherUpdate?.(data, locationKey);
    } catch (err) {
      setWeatherResult((previous) => ({
        locationKey,
        weather: previous.locationKey === locationKey
          ? previous.weather
          : null,
        error: err.message || "Unable to load weather data.",
      }));
    }
  }, [hasLocation, latitude, longitude, locationKey, onWeatherUpdate]);

  useEffect(() => {
    if (!hasLocation) return;

    fetchWeather();

    const interval = setInterval(fetchWeather, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, [fetchWeather, hasLocation, onWeatherUpdate]);

  const refreshWeather = async () => {
    setRefreshing(true);
    await fetchWeather();
    setRefreshing(false);
  };

  const getWeatherIcon = (condition) => {
    const text = (condition || "").toLowerCase();

    if (text.includes("thunderstorm")) return "⛈️";
    if (text.includes("rain") || text.includes("drizzle")) return "🌧️";
    if (text.includes("fog")) return "🌫️";
    if (text.includes("cloud") || text.includes("overcast")) return "☁️";
    if (text.includes("snow")) return "❄️";
    if (text.includes("clear")) return "☀️";

    return "🌤️";
  };

  if (!hasLocation) {
    return (
      <section className="weather-card">
        <h2>Weather</h2>
        <p>Choose a starting point or share your location to load weather.</p>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="weather-card">
        <h2>🌦️ Weather</h2>
        <p className="weather-loading">Loading weather data...</p>
      </section>
    );
  }

  if (error && !weather) {
    return (
      <section className="weather-card">
        <h2>🌦️ Weather</h2>
        <p className="weather-error">{error}</p>

        <button
          className="weather-refresh"
          onClick={fetchWeather}
          disabled={loading}
        >
          Retry
        </button>
      </section>
    );
  }

  return (
    <section className="weather-card">
      <div className="weather-header">
        <div>
          <h2>Weather Conditions</h2>
          <p className="weather-location">
            📍 {locationName || "Bengaluru, Karnataka"}
          </p>
        </div>

        <button
          className="weather-refresh"
          onClick={refreshWeather}
          disabled={refreshing}
        >
          {refreshing ? "Updating..." : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <p className="weather-warning">
          Refresh failed. Showing the last available data.
        </p>
      )}

      <div className="weather-main">
        <div className="weather-icon">
          {getWeatherIcon(weather.weather_condition)}
        </div>

        <div className="weather-temperature">
          {weather.temperature ?? "--"}°C
        </div>

        <h3>{weather.weather_condition || "Unknown"}</h3>

        <p className="weather-feels">
          Feels like {weather.feels_like ?? "--"}°C
        </p>
      </div>

      <div className="weather-grid">
        <div className="weather-item">
          <span>💧 Humidity</span>
          <strong>{weather.humidity ?? "--"}%</strong>
        </div>

        <div className="weather-item">
          <span>🌧️ Rainfall</span>
          <strong>{weather.rain ?? "--"} mm</strong>
        </div>

        <div className="weather-item">
          <span>🌦️ Precipitation</span>
          <strong>{weather.precipitation ?? "--"} mm</strong>
        </div>

        <div className="weather-item">
          <span>💨 Wind Speed</span>
          <strong>{weather.wind_speed ?? "--"} km/h</strong>
        </div>
      </div>

      <div className="weather-footer">
        <span>
          Last updated: {weather.time || "Unavailable"}
        </span>
      </div>
    </section>
  );
}