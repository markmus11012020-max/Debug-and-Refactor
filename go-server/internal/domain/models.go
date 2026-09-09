package domain

import "errors"

// Доменные ошибки сервиса.
var (
	ErrNotFound     = errors.New("not found")
	ErrInvalidInput = errors.New("invalid input")
	ErrConflict     = errors.New("conflict")
)

// User — модель пользователя доменного слоя.
type User struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
	Tags []string `json:"tags"`
}