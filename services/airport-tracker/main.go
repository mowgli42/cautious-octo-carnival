package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/mux"
)

const (
	Port              = ":3003"
	DefaultConfigPath = "/config/airports.json"
)

// FlightUpdate represents a flight update message from Pub/Sub
type FlightUpdate struct {
	ICAO24        string  `json:"icao24"`
	Callsign      string  `json:"callsign"`
	OriginCountry string  `json:"origin_country"`
	TimePosition  int64   `json:"time_position"`
	LastContact   int64   `json:"last_contact"`
	Longitude     float64 `json:"longitude"`
	Latitude      float64 `json:"latitude"`
	BaroAltitude  *float64 `json:"baro_altitude,omitempty"`
	GeoAltitude   *float64 `json:"geo_altitude,omitempty"`
	OnGround      bool    `json:"on_ground"`
	Velocity      *float64 `json:"velocity,omitempty"`
	TrueTrack     *float64 `json:"true_track,omitempty"`
	VerticalRate  *float64 `json:"vertical_rate,omitempty"`
	Squawk        string  `json:"squawk"`
	SPI           bool    `json:"spi"`
	PositionSource int    `json:"position_source"`
	Timestamp     int64   `json:"timestamp"`
}

// AirportConfig represents airport geofencing configuration
type AirportConfig struct {
	ICAO          string  `json:"icao"`
	Name          string  `json:"name"`
	Latitude      float64 `json:"latitude"`
	Longitude     float64 `json:"longitude"`
	RadiusKm      float64 `json:"radius_km"`
	ArrivalThresholdM  float64 `json:"arrival_threshold_m"`
	DepartureThresholdM float64 `json:"departure_threshold_m"`
}

// TrackedFlight represents a flight being tracked near an airport
type TrackedFlight struct {
	FlightUpdate
	AirportCode string    `json:"airport_code"`
	Status      string    `json:"status"` // "arriving", "departing", "nearby"
	LastSeen    time.Time `json:"last_seen"`
}

// AirportTracker service
type AirportTracker struct {
	airports     []AirportConfig
	flights      map[string]*TrackedFlight // key: icao24
	flightsMutex sync.RWMutex
	configPath   string
}

// CloudEvent represents Dapr CloudEvents format
type CloudEvent struct {
	Data      interface{} `json:"data"`
	DataBase64 string     `json:"data_base64,omitempty"`
}

func NewAirportTracker(configPath string) (*AirportTracker, error) {
	tracker := &AirportTracker{
		airports:   []AirportConfig{},
		flights:    make(map[string]*TrackedFlight),
		configPath: configPath,
	}
	
	if err := tracker.loadConfig(); err != nil {
		return nil, fmt.Errorf("failed to load airport config: %w", err)
	}
	
	return tracker, nil
}

func (at *AirportTracker) loadConfig() error {
	configPath := at.configPath
	if configPath == "" {
		configPath = os.Getenv("AIRPORT_CONFIG_PATH")
		if configPath == "" {
			configPath = DefaultConfigPath
		}
	}
	
	data, err := os.ReadFile(configPath)
	if err != nil {
		return fmt.Errorf("failed to read config file %s: %w", configPath, err)
	}
	
	if err := json.Unmarshal(data, &at.airports); err != nil {
		return fmt.Errorf("failed to parse config: %w", err)
	}
	
	log.Printf("✓ Loaded %d airports from %s", len(at.airports), configPath)
	return nil
}

// haversineDistance calculates distance between two points in kilometers
func haversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371 // Earth radius in km
	
	dLat := (lat2 - lat1) * math.Pi / 180
	dLon := (lon2 - lon1) * math.Pi / 180
	
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180)*math.Cos(lat2*math.Pi/180)*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return R * c
}

func (at *AirportTracker) processFlightUpdate(update FlightUpdate) {
	at.flightsMutex.Lock()
	defer at.flightsMutex.Unlock()
	
	for _, airport := range at.airports {
		distance := haversineDistance(
			update.Latitude,
			update.Longitude,
			airport.Latitude,
			airport.Longitude,
		)
		
		if distance <= airport.RadiusKm {
			altitude := 0.0
			if update.BaroAltitude != nil {
				altitude = *update.BaroAltitude
			} else if update.GeoAltitude != nil {
				altitude = *update.GeoAltitude
			}
			
			status := "nearby"
			if altitude > 0 && altitude < airport.ArrivalThresholdM {
				status = "arriving"
			} else if altitude > 0 && altitude < airport.DepartureThresholdM {
				status = "departing"
			}
			
			at.flights[update.ICAO24] = &TrackedFlight{
				FlightUpdate: update,
				AirportCode:  airport.ICAO,
				Status:       status,
				LastSeen:     time.Now(),
			}
			
			log.Printf("📍 Flight %s (%s) near %s - Status: %s (distance: %.2f km, altitude: %.0f m)",
				update.ICAO24, update.Callsign, airport.ICAO, status, distance, altitude)
		}
	}
}

// POST /flight-update - Dapr Pub/Sub subscription endpoint
func (at *AirportTracker) handleFlightUpdate(w http.ResponseWriter, r *http.Request) {
	// Dapr sends CloudEvents format - decode the raw body first
	var rawBody map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&rawBody); err != nil {
		http.Error(w, fmt.Sprintf("Failed to decode request: %v", err), http.StatusBadRequest)
		return
	}
	
	var flight FlightUpdate
	var dataBytes []byte
	var err error
	
	// Extract flight data from CloudEvents format
	// The data field can be a string (JSON) or an object
	if dataVal, ok := rawBody["data"]; ok {
		switch v := dataVal.(type) {
		case string:
			// Data is a JSON string
			dataBytes = []byte(v)
		case map[string]interface{}:
			// Data is already an object
			dataBytes, err = json.Marshal(v)
			if err != nil {
				http.Error(w, fmt.Sprintf("Failed to marshal data: %v", err), http.StatusBadRequest)
				return
			}
		default:
			http.Error(w, fmt.Sprintf("Unexpected data type: %T", v), http.StatusBadRequest)
			return
		}
		
		if err := json.Unmarshal(dataBytes, &flight); err != nil {
			http.Error(w, fmt.Sprintf("Failed to unmarshal flight data: %v", err), http.StatusBadRequest)
			return
		}
	} else if dataBase64, ok := rawBody["data_base64"].(string); ok {
		// Handle base64 encoded data (unlikely but possible)
		decoded, err := base64.StdEncoding.DecodeString(dataBase64)
		if err != nil {
			http.Error(w, fmt.Sprintf("Failed to decode base64 data: %v", err), http.StatusBadRequest)
			return
		}
		if err := json.Unmarshal(decoded, &flight); err != nil {
			http.Error(w, fmt.Sprintf("Failed to unmarshal flight data: %v", err), http.StatusBadRequest)
			return
		}
	} else {
		// Try to decode the entire body as flight data (fallback)
		bodyBytes, _ := json.Marshal(rawBody)
		if err := json.Unmarshal(bodyBytes, &flight); err != nil {
			http.Error(w, "No data field in CloudEvent and body is not flight data", http.StatusBadRequest)
			return
		}
	}
	
	at.processFlightUpdate(flight)
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "success"})
}

// GET /health - Health check endpoint
func (at *AirportTracker) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":  "healthy",
		"service": "airport-tracker",
	})
}

// GET /api/v1/airports - List all monitored airports
func (at *AirportTracker) handleListAirports(w http.ResponseWriter, r *http.Request) {
	at.flightsMutex.RLock()
	defer at.flightsMutex.RUnlock()
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(at.airports)
}

// GET /api/v1/airports/{code}/arrivals - Get flights arriving at airport
func (at *AirportTracker) handleArrivals(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	airportCode := vars["code"]
	
	at.flightsMutex.RLock()
	defer at.flightsMutex.RUnlock()
	
	arrivals := []TrackedFlight{}
	for _, flight := range at.flights {
		if flight.AirportCode == airportCode && flight.Status == "arriving" {
			arrivals = append(arrivals, *flight)
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"airport_code": airportCode,
		"arrivals":     arrivals,
		"count":        len(arrivals),
	})
}

// GET /api/v1/airports/{code}/departures - Get flights departing from airport
func (at *AirportTracker) handleDepartures(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	airportCode := vars["code"]
	
	at.flightsMutex.RLock()
	defer at.flightsMutex.RUnlock()
	
	departures := []TrackedFlight{}
	for _, flight := range at.flights {
		if flight.AirportCode == airportCode && flight.Status == "departing" {
			departures = append(departures, *flight)
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"airport_code": airportCode,
		"departures":   departures,
		"count":        len(departures),
	})
}

// GET /api/v1/airports/{code}/nearby - Get all flights near airport
func (at *AirportTracker) handleNearby(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	airportCode := vars["code"]
	
	at.flightsMutex.RLock()
	defer at.flightsMutex.RUnlock()
	
	nearby := []TrackedFlight{}
	for _, flight := range at.flights {
		if flight.AirportCode == airportCode {
			nearby = append(nearby, *flight)
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"airport_code": airportCode,
		"flights":      nearby,
		"count":        len(nearby),
	})
}

// GET /api/v1/flights/all - Get all tracked flights from all airports
func (at *AirportTracker) handleAllFlights(w http.ResponseWriter, r *http.Request) {
	at.flightsMutex.RLock()
	defer at.flightsMutex.RUnlock()
	
	allFlights := []TrackedFlight{}
	for _, flight := range at.flights {
		allFlights = append(allFlights, *flight)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"flights": allFlights,
		"count":   len(allFlights),
	})
}

func main() {
	configPath := os.Getenv("AIRPORT_CONFIG_PATH")
	if configPath == "" {
		configPath = DefaultConfigPath
	}
	
	tracker, err := NewAirportTracker(configPath)
	if err != nil {
		log.Fatalf("Failed to initialize airport tracker: %v", err)
	}
	
	router := mux.NewRouter()
	
	// Dapr Pub/Sub subscription endpoint
	router.HandleFunc("/flight-update", tracker.handleFlightUpdate).Methods("POST")
	
	// Health check
	router.HandleFunc("/health", tracker.handleHealth).Methods("GET")
	
	// REST API endpoints
	router.HandleFunc("/api/v1/airports", tracker.handleListAirports).Methods("GET")
	router.HandleFunc("/api/v1/airports/{code}/arrivals", tracker.handleArrivals).Methods("GET")
	router.HandleFunc("/api/v1/airports/{code}/departures", tracker.handleDepartures).Methods("GET")
	router.HandleFunc("/api/v1/airports/{code}/nearby", tracker.handleNearby).Methods("GET")
	router.HandleFunc("/api/v1/flights/all", tracker.handleAllFlights).Methods("GET")
	
	log.Printf("🚀 Airport Tracker service listening on port %s", Port)
	log.Printf("📡 Subscribing to flight-update topic via Dapr Pub/Sub")
	log.Printf("📍 Tracking %d airports", len(tracker.airports))
	
	if err := http.ListenAndServe(Port, router); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

