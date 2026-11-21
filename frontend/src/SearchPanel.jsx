import React, { useState, useEffect, useRef } from "react";
import "./SearchPanel.css";

const getApiBaseUrl = () => {
  const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
  const apiHost = host === "localhost" ? "127.0.0.1" : host;
  return `http://${apiHost}:8001`;
};
const RECENT_SEARCHES_KEY = "roadsafe_recent_searches";

export default function SearchPanel({
  startQuery,
  setStartQuery,
  destQuery,
  setDestQuery,
  onSelectStart,
  onSelectDest,
  onUseCurrentLocation,
  onGetDirections,
  onClearAll,
  loading,
  locationLoading,
  hasRoutes,
  tripStatus,
}) {
  const [activeInput, setActiveInput] = useState("dest"); // 'start' or 'dest'
  const [suggestions, setSuggestions] = useState([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  const debounceTimer = useRef(null);
  const dropdownRef = useRef(null);

  // Load recent searches on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(RECENT_SEARCHES_KEY);
      if (saved) {
        setRecentSearches(JSON.parse(saved));
      }
    } catch (e) {
      console.warn("Could not load recent searches", e);
    }
  }, []);

  const saveRecentSearch = (item) => {
    try {
      const filtered = recentSearches.filter((s) => s.display_name !== item.display_name);
      const updated = [item, ...filtered].slice(0, 5);
      setRecentSearches(updated);
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
    } catch (e) {
      console.warn("Could not save recent search", e);
    }
  };

  // Debounced geocoding search
  const fetchSuggestions = (query) => {
    clearTimeout(debounceTimer.current);

    if (!query || query.trim().length < 2 || /^\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*$/.test(query)) {
      setSuggestions([]);
      setSuggestLoading(false);
      return;
    }

    setSuggestLoading(true);
    debounceTimer.current = setTimeout(async () => {
      try {
        const response = await fetch(
          `${getApiBaseUrl()}/api/geocode?query=${encodeURIComponent(query.trim())}`
        );
        if (response.ok) {
          const data = await response.json();
          setSuggestions(data.locations || []);
        } else {
          setSuggestions([]);
        }
      } catch (err) {
        console.error("Autosuggest error:", err);
        setSuggestions([]);
      } finally {
        setSuggestLoading(false);
      }
    }, 300);
  };

  const handleInputChange = (type, value) => {
    setSelectedIndex(-1);
    setShowDropdown(true);
    if (type === "start") {
      setStartQuery(value);
      setActiveInput("start");
      fetchSuggestions(value);
    } else {
      setDestQuery(value);
      setActiveInput("dest");
      fetchSuggestions(value);
    }
  };

  const handleSelectLocation = (location) => {
    saveRecentSearch(location);
    setShowDropdown(false);
    setSuggestions([]);

    if (activeInput === "start") {
      setStartQuery(location.display_name);
      onSelectStart(location);
    } else {
      setDestQuery(location.display_name);
      onSelectDest(location);
    }
  };

  const handleKeyDown = (e) => {
    if (!showDropdown) return;

    const list = suggestions.length > 0 ? suggestions : recentSearches;
    if (!list.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < list.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : list.length - 1));
    } else if (e.key === "Enter") {
      if (selectedIndex >= 0 && selectedIndex < list.length) {
        e.preventDefault();
        handleSelectLocation(list[selectedIndex]);
      } else {
        e.preventDefault();
        onGetDirections();
        setShowDropdown(false);
      }
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  };

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentQuery = activeInput === "start" ? startQuery : destQuery;

  return (
    <div className={`search-panel-card${tripStatus === "in_progress" ? " is-navigating" : ""}`} ref={dropdownRef}>
      <div className="search-panel-header">
        <div className="search-panel-title">
          <svg className="nav-icon-logo" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
          </svg>
          <span>Bengaluru Navigator</span>
        </div>
        {tripStatus === "inactive" && (
          <button
            className="clear-all-btn"
            onClick={onClearAll}
            title="Clear inputs"
          >
            ✕
          </button>
        )}
        {tripStatus === "in_progress" && (
          <div className="nav-active-status">
            <div className="nav-active-dot" />
            <span>Navigating</span>
          </div>
        )}
      </div>

      {/* KARNATAKA SERVICE AREA LABEL */}
      {tripStatus === "inactive" && (
        <div className="service-area-label">
          <span className="service-area-icon">📍</span>
          <span>Service Area: Karnataka, India</span>
        </div>
      )}

      <div className="search-inputs-container">
        {/* Start Location Input */}
        <div className="search-field-group">
          <span className="field-dot start-dot" />
          <input
            type="text"
            className="search-input"
            placeholder="Starting location (default: Bengaluru Center)"
            value={startQuery}
            onChange={(e) => handleInputChange("start", e.target.value)}
            onFocus={() => {
              setActiveInput("start");
              setShowDropdown(true);
            }}
            onKeyDown={handleKeyDown}
            disabled={tripStatus !== "inactive"}
          />
          {startQuery && tripStatus === "inactive" && (
            <button
              className="field-clear-btn"
              onClick={() => {
                setStartQuery("");
                onSelectStart(null);
              }}
            >
              ✕
            </button>
          )}
          <button
            className="current-loc-btn"
            onClick={onUseCurrentLocation}
            title="Use current GPS location"
            disabled={locationLoading || tripStatus !== "inactive"}
          >
            {locationLoading ? (
              <span className="spinner-sm" />
            ) : (
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0013 3.06V1h-2v2.06A8.994 8.994 0 003.06 11H1v2h2.06A8.994 8.994 0 0011 20.94V23h2v-2.06A8.994 8.994 0 0020.94 13H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/>
              </svg>
            )}
          </button>
        </div>

        <div className="search-connector-line" />

        {/* Destination Input */}
        <div className="search-field-group">
          <span className="field-dot dest-dot" />
          <input
            type="text"
            className="search-input"
            placeholder="Search destination in Bengaluru..."
            value={destQuery}
            onChange={(e) => handleInputChange("dest", e.target.value)}
            onFocus={() => {
              setActiveInput("dest");
              setShowDropdown(true);
            }}
            onKeyDown={handleKeyDown}
            disabled={tripStatus !== "inactive"}
          />
          {destQuery && tripStatus === "inactive" && (
            <button
              className="field-clear-btn"
              onClick={() => {
                setDestQuery("");
                onSelectDest(null);
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Directions Action Button */}
      {tripStatus === "inactive" && (
        <button
          className="directions-primary-btn"
          onClick={onGetDirections}
          disabled={loading || (!startQuery && !destQuery)}
        >
          {loading ? (
            <>
              <span className="spinner-sm" /> Calculating Routes...
            </>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M21.71 11.29l-9-9a.996.996 0 00-1.41 0l-9 9a.996.996 0 000 1.41l9 9c.39.39 1.02.39 1.41 0l9-9a.996.996 0 000-1.41zM14 14.5V12h-4v3H8v-4c0-.55.45-1 1-1h5V7.5l3.5 3.5-3.5 3.5z"/>
              </svg>
              Get Directions
            </>
          )}
        </button>
      )}

      {/* Autocomplete Dropdown */}
      {showDropdown && tripStatus === "inactive" && (
        <div className="autocomplete-dropdown">
          {suggestLoading && (
            <div className="dropdown-loading">
              <span className="spinner-sm" /> Searching places...
            </div>
          )}

          {!suggestLoading && suggestions.length > 0 && (
            <div className="dropdown-section">
              <div className="dropdown-label">Suggestions</div>
              {suggestions.map((loc, idx) => (
                <div
                  key={idx}
                  className={`dropdown-item ${idx === selectedIndex ? "is-selected" : ""}`}
                  onClick={() => handleSelectLocation(loc)}
                >
                  <span className="item-icon">📍</span>
                  <div className="item-text">
                    <div className="item-title">{loc.display_name.split(",")[0]}</div>
                    <div className="item-sub">{loc.display_name}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!suggestLoading &&
            suggestions.length === 0 &&
            currentQuery.trim().length >= 2 &&
            !/^\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*$/.test(currentQuery) && (
              <div className="dropdown-no-results">No locations found in Bengaluru</div>
            )}

          {!suggestLoading &&
            suggestions.length === 0 &&
            recentSearches.length > 0 && (
              <div className="dropdown-section">
                <div className="dropdown-label">Recent Searches</div>
                {recentSearches.map((loc, idx) => (
                  <div
                    key={`recent-${idx}`}
                    className={`dropdown-item ${idx === selectedIndex ? "is-selected" : ""}`}
                    onClick={() => handleSelectLocation(loc)}
                  >
                    <span className="item-icon">🕒</span>
                    <div className="item-text">
                      <div className="item-title">{loc.display_name.split(",")[0]}</div>
                      <div className="item-sub">{loc.display_name}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
        </div>
      )}
    </div>
  );
}
