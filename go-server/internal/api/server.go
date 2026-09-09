package api

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"go-server/internal/domain"
	"go-server/internal/store"
)

// Server инкапсулирует зависимости HTTP-слоя.
type Server struct {
	users    *store.SQLiteStore
	passwords *store.PasswordStore
	active   *store.ActiveUsers
}

func NewServer(u *store.SQLiteStore, p *store.PasswordStore, a *store.ActiveUsers) *Server {
	return &Server{users: u, passwords: p, active: a}
}

// Routes возвращает корневой http.Handler с middleware.
func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", s.health)

	mux.HandleFunc("/users", s.usersCollection)
	mux.HandleFunc("/users/", s.usersItem)

	mux.HandleFunc("/active", s.activeUsers)

	return chain(mux, logging, recoverer)
}

// --- handlers ---

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, badRequest("method not allowed"))
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// /users  -> POST создать / GET список
func (s *Server) usersCollection(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		s.createUser(w, r)
	case http.MethodGet:
		s.listUsers(w, r)
	default:
		writeError(w, badRequest("method not allowed"))
	}
}

// /users/<id>                 -> GET
// /users/<id>/password        -> POST
func (s *Server) usersItem(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 2 || parts[0] != "users" {
		writeError(w, notFound("not found"))
		return
	}
	id, err := strconv.Atoi(parts[1])
	if err != nil {
		writeError(w, validation("invalid user id"))
		return
	}

	if len(parts) == 2 {
		if r.Method != http.MethodGet {
			writeError(w, badRequest("method not allowed"))
			return
		}
		s.getUser(w, id)
		return
	}

	if len(parts) == 3 && parts[2] == "password" {
		if r.Method != http.MethodPost {
			writeError(w, badRequest("method not allowed"))
			return
		}
		s.setPassword(w, id, r)
		return
	}

	writeError(w, notFound("not found"))
}

func (s *Server) activeUsers(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, badRequest("method not allowed"))
		return
	}
	writeJSON(w, http.StatusOK, s.active.Snapshot())
}

// --- service-level handlers ---

func (s *Server) createUser(w http.ResponseWriter, r *http.Request) {
	var payload struct {
		Name string   `json:"name"`
		Tags []string `json:"tags"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, validation("invalid JSON body"))
		return
	}
	name := strings.TrimSpace(payload.Name)
	if name == "" {
		writeError(w, validation("'name' is required"))
		return
	}
	if len(name) > 64 {
		writeError(w, validation("'name' too long"))
		return
	}
	if len(payload.Tags) > 16 {
		writeError(w, validation("too many tags"))
		return
	}
	tags := make([]string, 0, len(payload.Tags))
	for _, t := range payload.Tags {
		t = strings.TrimSpace(t)
		if t == "" {
			writeError(w, validation("tag must be non-empty"))
			return
		}
		if len(t) > 32 {
			writeError(w, validation("tag too long"))
			return
		}
		tags = append(tags, t)
	}

	id, err := s.users.AddUser(name, tags)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			writeError(w, conflict("user already exists"))
			return
		}
		writeError(w, internal(err.Error()))
		return
	}

	s.active.Add(id)

	user, err := s.users.GetByID(id)
	if err != nil {
		writeError(w, internal(err.Error()))
		return
	}
	writeJSON(w, http.StatusCreated, user)
}

func (s *Server) listUsers(w http.ResponseWriter, _ *http.Request) {
	users, err := s.users.List()
	if err != nil {
		writeError(w, internal(err.Error()))
		return
	}
	if users == nil {
		users = []domain.User{}
	}
	writeJSON(w, http.StatusOK, users)
}

func (s *Server) getUser(w http.ResponseWriter, id int) {
	user, err := s.users.GetByID(id)
	if err != nil {
		if err == domain.ErrNotFound {
			writeError(w, notFound("user "+strconv.Itoa(id)+" not found"))
			return
		}
		writeError(w, internal(err.Error()))
		return
	}
	writeJSON(w, http.StatusOK, user)
}

func (s *Server) setPassword(w http.ResponseWriter, id int, r *http.Request) {
	if _, err := s.users.GetByID(id); err != nil {
		if err == domain.ErrNotFound {
			writeError(w, notFound("user "+strconv.Itoa(id)+" not found"))
			return
		}
		writeError(w, internal(err.Error()))
		return
	}

	var payload struct {
		Password string `json:"password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, validation("invalid JSON body"))
		return
	}
	if payload.Password == "" {
		writeError(w, validation("'password' is required"))
		return
	}

	hashed, err := s.passwords.Store(id, payload.Password)
	if err != nil {
		writeError(w, internal(err.Error()))
		return
	}
	preview := hashed
	if len(preview) > 7 {
		preview = preview[:7] + "..."
	}
	writeJSON(w, http.StatusCreated, map[string]any{
		"id":      id,
		"hashed":  true,
		"preview": preview,
	})
}