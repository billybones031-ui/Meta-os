// Meta-OS Go Observer
// Listens on :8081
//
// POST /log   — append a JSON entry to system_logs.jsonl
// GET  /logs  — stream the last N lines of system_logs.jsonl
// GET  /health — liveness probe
//
// Log entry schema (all fields optional except "message"):
//   { "ts": "<RFC3339>", "level": "info|warn|error", "source": "...", "message": "..." }

package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"
)

const (
	defaultPort    = "8081"
	defaultLogFile = "system_logs.jsonl"
)

var (
	logFile string
	mu      sync.Mutex // guards file writes
)

type LogEntry struct {
	Ts      string `json:"ts"`
	Level   string `json:"level,omitempty"`
	Source  string `json:"source,omitempty"`
	Message string `json:"message"`
}

func appendLog(entry LogEntry) error {
	if entry.Ts == "" {
		entry.Ts = time.Now().UTC().Format(time.RFC3339)
	}
	if entry.Level == "" {
		entry.Level = "info"
	}

	b, err := json.Marshal(entry)
	if err != nil {
		return err
	}

	mu.Lock()
	defer mu.Unlock()

	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	_, err = fmt.Fprintf(f, "%s\n", b)
	return err
}

// lastLines reads the last n lines from a file efficiently.
func lastLines(path string, n int) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	defer f.Close()

	var lines []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	if len(lines) <= n {
		return lines, nil
	}
	return lines[len(lines)-n:], nil
}

// -------------------------------------------------------------------------- //
// Handlers
// -------------------------------------------------------------------------- //

func handleLog(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<16))
	if err != nil {
		http.Error(w, "read error", http.StatusBadRequest)
		return
	}

	var entry LogEntry
	if err := json.Unmarshal(body, &entry); err != nil {
		// Treat raw string as message
		entry = LogEntry{Message: string(body)}
	}
	if entry.Message == "" {
		http.Error(w, "message required", http.StatusBadRequest)
		return
	}

	if err := appendLog(entry); err != nil {
		http.Error(w, "write error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	fmt.Fprintf(w, `{"status":"logged"}`)
}

func handleLogs(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	n := 50
	if v := r.URL.Query().Get("n"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 {
			n = parsed
		}
	}

	lines, err := lastLines(logFile, n)
	if err != nil {
		http.Error(w, "read error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/x-ndjson")
	for _, line := range lines {
		fmt.Fprintf(w, "%s\n", line)
	}
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"status":"ok","service":"observer"}`)
}

// -------------------------------------------------------------------------- //
// Main
// -------------------------------------------------------------------------- //

func main() {
	port := os.Getenv("OBSERVER_PORT")
	if port == "" {
		port = defaultPort
	}

	logDir := os.Getenv("LOG_DIR")
	if logDir == "" {
		logDir = "."
	}
	logFile = filepath.Join(logDir, defaultLogFile)

	mux := http.NewServeMux()
	mux.HandleFunc("/log", handleLog)
	mux.HandleFunc("/logs", handleLogs)
	mux.HandleFunc("/health", handleHealth)

	addr := ":" + port
	log.Printf("Meta-OS Observer listening on %s — logging to %s\n", addr, logFile)

	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
