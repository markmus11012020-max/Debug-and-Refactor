package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config — единая конфигурация сервера. Читается из ENV / .env.
type Config struct {
	DBPath        string
	PasswordsFile string
	BcryptCost    int
	ActiveMaxLen  int

	Host    string
	Port    int
	Debug   bool
	Timeout time.Duration
}

func env(key, def string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envBool(key string, def bool) bool {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		switch strings.ToLower(v) {
		case "1", "true", "yes", "on":
			return true
		case "0", "false", "no", "off":
			return false
		}
	}
	return def
}

func Load() Config {
	return Config{
		DBPath:        env("DB_PATH", "users.db"),
		PasswordsFile: env("PASSWORDS_FILE", "passwords.txt"),
		BcryptCost:    envInt("BCRYPT_ROUNDS", 12),
		ActiveMaxLen:  envInt("ACTIVE_USERS_MAXLEN", 5),
		Host:          env("API_HOST", "127.0.0.1"),
		Port:          envInt("API_PORT", 5000),
		Debug:         envBool("API_DEBUG", false),
		Timeout:       15 * time.Second,
	}
}

func (c Config) Addr() string { return fmt.Sprintf("%s:%d", c.Host, c.Port) }