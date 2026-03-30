package main

import (
	"testing"
)

func TestFindExecutable(t *testing.T) {
	// Should find common binaries
	path, err := findExecutable("sh")
	if err != nil {
		t.Fatalf("expected to find sh: %v", err)
	}
	if path == "" {
		t.Fatal("expected non-empty path for sh")
	}

	// Should handle absolute paths
	path, err = findExecutable("/bin/sh")
	if err != nil {
		t.Fatalf("expected to find /bin/sh: %v", err)
	}
	if path != "/bin/sh" {
		t.Fatalf("expected /bin/sh, got %s", path)
	}

	// Should error on missing commands
	_, err = findExecutable("nonexistent-command-12345")
	if err == nil {
		t.Fatal("expected error for nonexistent command")
	}

	// Should error on missing relative paths
	_, err = findExecutable("./nonexistent")
	if err == nil {
		t.Fatal("expected error for ./nonexistent")
	}
}
