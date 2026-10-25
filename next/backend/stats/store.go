// Package stats records the robot's history in SQLite: a sample of battery,
// current and GPS every minute for the charts, and per hour how much the
// firmware counters (AT+T: mow time, distance, obstacles …) grew.
package stats

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"

	_ "modernc.org/sqlite" // pure Go, no C toolchain
)

// schemaVersion is stored in PRAGMA user_version; bump it with a migration.
const schemaVersion = 1

// Sample is one reading of the robot.
type Sample struct {
	T             time.Time `json:"t"`
	BatteryV      float64   `json:"batteryV"`
	Amps          float64   `json:"amps"`
	Satellites    float64   `json:"satellites"`
	AccuracyM     float64   `json:"accuracyM"`
	LateralErrorM float64   `json:"lateralErrorM"`
}

// Store is the statistics database. Safe for concurrent use.
type Store struct {
	db *sql.DB
}

// Open opens or creates the database at path. A file that is not a database
// of this app fails.
func Open(path string) (*Store, error) {
	// Created here with 0600 like every other file of the data directory.
	f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, fmt.Errorf("open stats: %w", err)
	}
	_ = f.Close()
	db, err := sql.Open("sqlite", "file:"+path+"?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)&_pragma=synchronous(NORMAL)")
	if err != nil {
		return nil, fmt.Errorf("open stats: %w", err)
	}
	db.SetMaxOpenConns(1) // one writer; the database is small and local
	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("open stats %s: %w", path, err)
	}
	return s, nil
}

// Close closes the database.
func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) migrate() error {
	var version int
	if err := s.db.QueryRow("PRAGMA user_version").Scan(&version); err != nil {
		return err
	}
	switch version {
	case schemaVersion:
		return nil
	case 0:
	default:
		return fmt.Errorf("unknown schema version %d", version)
	}
	cols := make([]string, 0, len(counters)+len(maxima))
	for _, c := range counters {
		cols = append(cols, c.column+" REAL NOT NULL DEFAULT 0")
	}
	for _, m := range maxima {
		cols = append(cols, m.column+" REAL NOT NULL DEFAULT 0")
	}
	stmts := []string{
		`CREATE TABLE samples (t INTEGER PRIMARY KEY, battery_v REAL, amps REAL, satellites REAL,
			accuracy_m REAL, lateral_error_m REAL)`,
		`CREATE TABLE hours (t INTEGER PRIMARY KEY, ` + strings.Join(cols, ", ") + `)`,
		`CREATE TABLE baseline (id INTEGER PRIMARY KEY CHECK (id = 1), stats TEXT NOT NULL)`,
		fmt.Sprintf("PRAGMA user_version = %d", schemaVersion),
	}
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	for _, q := range stmts {
		if _, err := tx.Exec(q); err != nil {
			return err
		}
	}
	return tx.Commit()
}

// AddSample stores a reading; a second one with the same time replaces it.
func (s *Store) AddSample(ctx context.Context, x Sample) error {
	_, err := s.db.ExecContext(ctx, `INSERT OR REPLACE INTO samples VALUES (?, ?, ?, ?, ?, ?)`,
		x.T.UnixMilli(), x.BatteryV, x.Amps, x.Satellites, x.AccuracyM, x.LateralErrorM)
	if err != nil {
		return fmt.Errorf("add sample: %w", err)
	}
	return nil
}

// AddStats adds how much the counters grew since the last report to the hour
// of t. The first report only sets the starting point.
func (s *Store) AddStats(ctx context.Context, t time.Time, now protocol.Stats) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("add stats: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	var raw string
	err = tx.QueryRowContext(ctx, `SELECT stats FROM baseline WHERE id = 1`).Scan(&raw)
	switch {
	case errors.Is(err, sql.ErrNoRows):
	case err != nil:
		return fmt.Errorf("add stats: %w", err)
	default:
		var old protocol.Stats
		if err := json.Unmarshal([]byte(raw), &old); err != nil {
			return fmt.Errorf("add stats: baseline: %w", err)
		}
		if err := addHour(ctx, tx, t, old, now); err != nil {
			return fmt.Errorf("add stats: %w", err)
		}
	}
	b, err := json.Marshal(now)
	if err != nil {
		return fmt.Errorf("add stats: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `INSERT OR REPLACE INTO baseline VALUES (1, ?)`, string(b)); err != nil {
		return fmt.Errorf("add stats: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("add stats: %w", err)
	}
	return nil
}

func addHour(ctx context.Context, tx *sql.Tx, t time.Time, old, now protocol.Stats) error {
	names := []string{"t"}
	marks := []string{"?"}
	sets := make([]string, 0, len(counters)+len(maxima))
	args := []any{t.Truncate(time.Hour).UnixMilli()}
	for _, c := range counters {
		names, marks = append(names, c.column), append(marks, "?")
		sets = append(sets, fmt.Sprintf("%[1]s = %[1]s + excluded.%[1]s", c.column))
		args = append(args, growth(c.get(old), c.get(now)))
	}
	for _, m := range maxima {
		names, marks = append(names, m.column), append(marks, "?")
		sets = append(sets, fmt.Sprintf("%[1]s = max(%[1]s, excluded.%[1]s)", m.column))
		args = append(args, m.get(now))
	}
	q := `INSERT INTO hours (` + strings.Join(names, ", ") + `) VALUES (` + strings.Join(marks, ", ") +
		`) ON CONFLICT (t) DO UPDATE SET ` + strings.Join(sets, ", ")
	_, err := tx.ExecContext(ctx, q, args...)
	return err
}

// Samples returns the readings in [from, to), averaged over buckets so that
// at most points come back (at least one bucket per minute).
func (s *Store) Samples(ctx context.Context, from, to time.Time, points int) ([]Sample, error) {
	bucket := max(to.Sub(from).Milliseconds()/int64(max(points, 1)), time.Minute.Milliseconds())
	rows, err := s.db.QueryContext(ctx, `SELECT (t / ?) * ? AS b, avg(battery_v), avg(amps), avg(satellites),
		avg(accuracy_m), avg(lateral_error_m) FROM samples WHERE t >= ? AND t < ? GROUP BY b ORDER BY b`,
		bucket, bucket, from.UnixMilli(), to.UnixMilli())
	if err != nil {
		return nil, fmt.Errorf("samples: %w", err)
	}
	defer func() { _ = rows.Close() }()
	out := []Sample{}
	for rows.Next() {
		var ms int64
		var x Sample
		if err := rows.Scan(&ms, &x.BatteryV, &x.Amps, &x.Satellites, &x.AccuracyM, &x.LateralErrorM); err != nil {
			return nil, fmt.Errorf("samples: %w", err)
		}
		x.T = time.UnixMilli(ms)
		out = append(out, x)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("samples: %w", err)
	}
	return out, nil
}

// Totals returns how much each counter grew in the hours that start in
// [from, to), and the highest maxima; keys are the JSON names.
func (s *Store) Totals(ctx context.Context, from, to time.Time) (map[string]float64, error) {
	exprs := make([]string, 0, len(counters)+len(maxima))
	for _, c := range counters {
		exprs = append(exprs, "coalesce(sum("+c.column+"), 0)")
	}
	for _, m := range maxima {
		exprs = append(exprs, "coalesce(max("+m.column+"), 0)")
	}
	vals := make([]float64, len(exprs))
	dest := make([]any, len(vals))
	for i := range vals {
		dest[i] = &vals[i]
	}
	q := `SELECT ` + strings.Join(exprs, ", ") + ` FROM hours WHERE t >= ? AND t < ?`
	if err := s.db.QueryRowContext(ctx, q, from.Truncate(time.Hour).UnixMilli(), to.UnixMilli()).Scan(dest...); err != nil {
		return nil, fmt.Errorf("totals: %w", err)
	}
	out := make(map[string]float64, len(vals))
	for i, c := range append(append([]counter{}, counters...), maxima...) {
		out[c.name] = vals[i]
	}
	return out, nil
}

// Prune deletes the samples older than before; the hourly totals stay.
func (s *Store) Prune(ctx context.Context, before time.Time) error {
	if _, err := s.db.ExecContext(ctx, `DELETE FROM samples WHERE t < ?`, before.UnixMilli()); err != nil {
		return fmt.Errorf("prune samples: %w", err)
	}
	return nil
}
