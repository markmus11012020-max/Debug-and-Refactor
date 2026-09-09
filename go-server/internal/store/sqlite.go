package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"sync"

	_ "modernc.org/sqlite"

	"go-server/internal/domain"
)

// SQLiteStore — потокобезопасное хранилище пользователей поверх SQLite.
// Используется чистый Go-драйвер modernc.org/sqlite (без CGO).
type SQLiteStore struct {
	mu sync.Mutex
	db *sql.DB
}

func NewSQLite(path string) (*SQLiteStore, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	db.SetMaxOpenConns(1) // SQLite + WAL — простой и предсказуемый режим
	s := &SQLiteStore{db: db}
	if err := s.migrate(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

func (s *SQLiteStore) Close() error { return s.db.Close() }

func (s *SQLiteStore) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS users (
			id   INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL UNIQUE,
			tags TEXT NOT NULL DEFAULT '[]'
		)
	`)
	return err
}

func (s *SQLiteStore) AddUser(name string, tags []string) (int, error) {
	tagsCopy := append([]string(nil), tags...)
	tagsCopy = append(tagsCopy, "new")
	raw, _ := json.Marshal(tagsCopy)

	res, err := s.db.Exec(
		`INSERT INTO users (name, tags) VALUES (?, ?)`,
		name, string(raw),
	)
	if err != nil {
		return 0, err
	}
	id, _ := res.LastInsertId()
	return int(id), nil
}

func scanUser(row *sql.Row) (*domain.User, error) {
	var id int
	var name, raw string
	if err := row.Scan(&id, &name, &raw); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, domain.ErrNotFound
		}
		return nil, err
	}
	tags := []string{}
	_ = json.Unmarshal([]byte(raw), &tags)
	return &domain.User{ID: id, Name: name, Tags: tags}, nil
}

func (s *SQLiteStore) GetByName(name string) (*domain.User, error) {
	row := s.db.QueryRow(`SELECT id, name, tags FROM users WHERE name = ?`, name)
	return scanUser(row)
}

func (s *SQLiteStore) GetByID(id int) (*domain.User, error) {
	row := s.db.QueryRow(`SELECT id, name, tags FROM users WHERE id = ?`, id)
	return scanUser(row)
}

func (s *SQLiteStore) DeleteByName(name string) (int64, error) {
	res, err := s.db.Exec(`DELETE FROM users WHERE name = ?`, name)
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}

func (s *SQLiteStore) List() ([]domain.User, error) {
	rows, err := s.db.Query(`SELECT id, name, tags FROM users ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.User, 0)
	for rows.Next() {
		var id int
		var name, raw string
		if err := rows.Scan(&id, &name, &raw); err != nil {
			return nil, err
		}
		tags := []string{}
		_ = json.Unmarshal([]byte(raw), &tags)
		out = append(out, domain.User{ID: id, Name: name, Tags: tags})
	}
	return out, rows.Err()
}