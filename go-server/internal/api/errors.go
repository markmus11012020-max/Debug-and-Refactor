package api

import (
	"encoding/json"
	"net/http"
)

// APIError — ошибка API с HTTP-кодом.
type APIError struct {
	Status  int    `json:"-"`
	Message string `json:"error"`
}

func (e *APIError) Error() string { return e.Message }

func badRequest(msg string) *APIError    { return &APIError{Status: http.StatusBadRequest, Message: msg} }
func notFound(msg string) *APIError      { return &APIError{Status: http.StatusNotFound, Message: msg} }
func conflict(msg string) *APIError      { return &APIError{Status: http.StatusConflict, Message: msg} }
func validation(msg string) *APIError    { return &APIError{Status: http.StatusUnprocessableEntity, Message: msg} }
func internal(msg string) *APIError      { return &APIError{Status: http.StatusInternalServerError, Message: msg} }

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, err error) {
	if e, ok := err.(*APIError); ok {
		writeJSON(w, e.Status, e)
		return
	}
	writeJSON(w, http.StatusInternalServerError, &APIError{Message: "internal server error"})
}