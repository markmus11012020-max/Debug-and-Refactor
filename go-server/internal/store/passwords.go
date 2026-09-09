package store

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"golang.org/x/crypto/bcrypt"
)

// PasswordStore — потокобезопасный файл-хеш bcrypt-хешей.
// Формат строки: "<user_id>:<bcrypt_hash>".
type PasswordStore struct {
	mu   sync.Mutex
	path string
	cost int
}

func NewPasswordStore(path string, cost int) *PasswordStore {
	if cost < bcrypt.MinCost {
		cost = bcrypt.DefaultCost
	}
	return &PasswordStore{path: path, cost: cost}
}

func (p *PasswordStore) Store(userID int, password string) (string, error) {
	if password == "" {
		return "", errors.New("password must be non-empty")
	}
	h, err := bcrypt.GenerateFromPassword([]byte(password), p.cost)
	if err != nil {
		return "", err
	}
	hash := string(h)

	p.mu.Lock()
	defer p.mu.Unlock()

	if err := os.MkdirAll(filepath.Dir(p.path), 0o755); err != nil {
		return "", err
	}
	f, err := os.OpenFile(p.path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o600)
	if err != nil {
		return "", err
	}
	defer f.Close()
	if _, err := f.WriteString(fmt.Sprintf("%d:%s\n", userID, hash)); err != nil {
		return "", err
	}
	return hash, nil
}

func (p *PasswordStore) FindHash(userID int) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	data, err := os.ReadFile(p.path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return "", nil
		}
		return "", err
	}
	prefix := fmt.Sprintf("%d:", userID)
	for i := 0; i < len(data); {
		j := i
		for j < len(data) && data[j] != '\n' {
			j++
		}
		line := string(data[i:j])
		if len(line) >= len(prefix) && line[:len(prefix)] == prefix {
			return line[len(prefix):], nil
		}
		i = j + 1
	}
	return "", nil
}

func (p *PasswordStore) Verify(userID int, password string) bool {
	hash, err := p.FindHash(userID)
	if err != nil || hash == "" {
		return false
	}
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password)) == nil
}