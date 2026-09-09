package tests

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"go-server/internal/api"
	"go-server/internal/store"
)

func newTestServer(t *testing.T) (*httptest.Server, func()) {
	t.Helper()
	dir := t.TempDir()
	users, err := store.NewSQLite(filepath.Join(dir, "u.db"))
	if err != nil {
		t.Fatalf("sqlite: %v", err)
	}
	pwd := store.NewPasswordStore(filepath.Join(dir, "p.txt"), 4)
	active := store.NewActiveUsers(3)

	srv := httptest.NewServer(api.NewServer(users, pwd, active).Routes())
	cleanup := func() {
		srv.Close()
		_ = users.Close()
	}
	return srv, cleanup
}

func TestHealth(t *testing.T) {
	srv, done := newTestServer(t)
	defer done()
	r, _ := http.Get(srv.URL + "/health")
	if r.StatusCode != 200 {
		t.Fatalf("status=%d", r.StatusCode)
	}
	var body map[string]string
	_ = json.NewDecoder(r.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Fatalf("unexpected body: %v", body)
	}
}

func TestCreateAndGetUser(t *testing.T) {
	srv, done := newTestServer(t)
	defer done()

	body := bytes.NewBufferString(`{"name":"alice","tags":["vip"]}`)
	r, _ := http.Post(srv.URL+"/users", "application/json", body)
	if r.StatusCode != 201 {
		t.Fatalf("create status=%d", r.StatusCode)
	}
	var u map[string]any
	_ = json.NewDecoder(r.Body).Decode(&u)
	if u["name"] != "alice" {
		t.Fatalf("name=%v", u["name"])
	}
	idF, _ := u["id"].(float64)
	id := int(idF)

	r2, _ := http.Get(srv.URL + "/users/" + itoa(id))
	if r2.StatusCode != 200 {
		t.Fatalf("get status=%d", r2.StatusCode)
	}
}

func TestValidationMissingName(t *testing.T) {
	srv, done := newTestServer(t)
	defer done()
	r, _ := http.Post(srv.URL+"/users", "application/json", strings.NewReader(`{}`))
	if r.StatusCode != 422 {
		t.Fatalf("status=%d", r.StatusCode)
	}
}

func TestGetUserNotFound(t *testing.T) {
	srv, done := newTestServer(t)
	defer done()
	r, _ := http.Get(srv.URL + "/users/999")
	if r.StatusCode != 404 {
		t.Fatalf("status=%d", r.StatusCode)
	}
}

func TestSQLInjectionIsNeutralized(t *testing.T) {
	srv, done := newTestServer(t)
	defer done()
	body := bytes.NewBufferString(`{"name":"x'); DROP TABLE users;--"}`)
	r, _ := http.Post(srv.URL+"/users", "application/json", body)
	if r.StatusCode != 201 {
		t.Fatalf("status=%d", r.StatusCode)
	}
	r2, _ := http.Get(srv.URL + "/users")
	if r2.StatusCode != 200 {
		t.Fatalf("status=%d", r2.StatusCode)
	}
}

func TestSetPasswordAndActive(t *testing.T) {
	srv, done := newTestServer(t)
	defer done()
	body := bytes.NewBufferString(`{"name":"carol"}`)
	r, _ := http.Post(srv.URL+"/users", "application/json", body)
	var u map[string]any
	_ = json.NewDecoder(r.Body).Decode(&u)
	id := int(u["id"].(float64))

	rp, _ := http.Post(srv.URL+"/users/"+itoa(id)+"/password", "application/json",
		strings.NewReader(`{"password":"hunter2"}`))
	if rp.StatusCode != 201 {
		t.Fatalf("password status=%d", rp.StatusCode)
	}

	ra, _ := http.Get(srv.URL + "/active")
	if ra.StatusCode != 200 {
		t.Fatalf("active status=%d", ra.StatusCode)
	}
}

func itoa(i int) string {
	return strings.TrimSpace(formatInt(i))
}

func formatInt(i int) string {
	// минимальная замена strconv.Itoa, чтобы не тянуть импорт
	if i == 0 {
		return "0"
	}
	neg := i < 0
	if neg {
		i = -i
	}
	buf := [20]byte{}
	pos := len(buf)
	for i > 0 {
		pos--
		buf[pos] = byte('0' + i%10)
		i /= 10
	}
	if neg {
		pos--
		buf[pos] = '-'
	}
	return string(buf[pos:])
}