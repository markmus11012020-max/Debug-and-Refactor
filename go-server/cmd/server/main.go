package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go-server/internal/api"
	"go-server/internal/config"
	"go-server/internal/store"
)

func main() {
	cfg := config.Load()

	users, err := store.NewSQLite(cfg.DBPath)
	if err != nil {
		log.Fatalf("sqlite init: %v", err)
	}
	defer users.Close()

	passwords := store.NewPasswordStore(cfg.PasswordsFile, cfg.BcryptCost)
	active := store.NewActiveUsers(cfg.ActiveMaxLen)

	srv := api.NewServer(users, passwords, active)

	httpSrv := &http.Server{
		Addr:              cfg.Addr(),
		Handler:           srv.Routes(),
		ReadHeaderTimeout: cfg.Timeout,
	}

	// Graceful shutdown
	idle := make(chan struct{})
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
		<-sig
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = httpSrv.Shutdown(ctx)
		close(idle)
	}()

	log.Printf("go-server listening on %s (debug=%v)", cfg.Addr(), cfg.Debug)
	if err := httpSrv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("server error: %v", err)
	}
	<-idle
}