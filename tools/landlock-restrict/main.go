// landlock-restrict is a CLI wrapper that applies Linux Landlock filesystem
// restrictions before exec'ing a command. It restricts the command (and all
// child processes) to only access explicitly allowed paths.
//
// Usage:
//
//	landlock-restrict --rw /tmp --rw /shared -- command args...
package main

import (
	"fmt"
	"os"
	"strings"
	"syscall"

	"github.com/landlock-lsm/go-landlock/landlock"
)

// defaultROPaths are system paths granted read-only access automatically
// so that dynamically-linked binaries (Node.js, bash, etc.) can start.
var defaultROPaths = []string{
	"/usr",
	"/bin",
	"/lib",
	"/lib64",
	"/etc",
	"/dev",
	"/proc",
	"/sys",
	"/home",
	"/opt",
}

func usage() {
	fmt.Fprintf(os.Stderr, `Usage: landlock-restrict [options] -- command [args...]

Apply Landlock filesystem restrictions before exec'ing a command.
The command and all child processes are restricted to only the allowed paths.

Options:
  --ro PATH          Allow read-only access to PATH (repeatable)
  --rw PATH          Allow read-write access to PATH (repeatable)
  --no-defaults      Do not include default read-only system paths

By default, common system paths (/usr, /bin, /lib, /lib64, /etc, /dev,
/proc, /sys, /home, /opt) are granted read-only access so that programs
can start normally. Use --no-defaults to disable this.

All paths not explicitly allowed are denied. Restrictions are inherited
by child processes and cannot be removed.

If the kernel does not support Landlock, the command exits with an error.

Examples:
  landlock-restrict --rw /tmp -- ls /tmp
  landlock-restrict --rw /tmp --rw /shared -- claude -p "hello"
  landlock-restrict --no-defaults --ro /usr --rw /tmp -- command
`)
	os.Exit(2)
}

func main() {
	var roPaths, rwPaths []string
	var cmdStart int
	noDefaults := false

	args := os.Args[1:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--":
			cmdStart = i + 1
			goto done
		case "--ro":
			if i+1 >= len(args) {
				fmt.Fprintf(os.Stderr, "error: --ro requires a path argument\n")
				os.Exit(2)
			}
			i++
			roPaths = append(roPaths, args[i])
		case "--rw":
			if i+1 >= len(args) {
				fmt.Fprintf(os.Stderr, "error: --rw requires a path argument\n")
				os.Exit(2)
			}
			i++
			rwPaths = append(rwPaths, args[i])
		case "--no-defaults":
			noDefaults = true
		case "--help", "-h":
			usage()
		default:
			if strings.HasPrefix(args[i], "-") {
				fmt.Fprintf(os.Stderr, "error: unknown option %q\n", args[i])
				os.Exit(2)
			}
			// No --, treat rest as command
			cmdStart = i
			goto done
		}
	}
done:

	if cmdStart >= len(args) {
		fmt.Fprintf(os.Stderr, "error: no command specified\n")
		usage()
	}

	cmd := args[cmdStart:]

	// Add default system paths unless --no-defaults was specified
	if !noDefaults {
		roPaths = append(defaultROPaths, roPaths...)
	}

	if len(roPaths) == 0 && len(rwPaths) == 0 {
		fmt.Fprintf(os.Stderr, "error: no paths specified, use --ro and/or --rw\n")
		os.Exit(2)
	}

	// Resolve the executable path before applying restrictions,
	// since Landlock may block access to directories in PATH.
	execPath, err := findExecutable(cmd[0])
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}

	var rules []landlock.Rule
	if len(roPaths) > 0 {
		rules = append(rules, landlock.RODirs(roPaths...).IgnoreIfMissing())
	}
	if len(rwPaths) > 0 {
		rules = append(rules, landlock.RWDirs(rwPaths...).IgnoreIfMissing())
	}

	if err := landlock.V5.RestrictPaths(rules...); err != nil {
		fmt.Fprintf(os.Stderr, "error: failed to apply landlock restrictions: %v\n", err)
		os.Exit(1)
	}

	fmt.Fprintf(os.Stderr, "landlock: restricted to ro=%v rw=%v\n", roPaths, rwPaths)

	if err := syscall.Exec(execPath, cmd, os.Environ()); err != nil {
		fmt.Fprintf(os.Stderr, "error: exec %s: %v\n", cmd[0], err)
		os.Exit(1)
	}
}

// findExecutable resolves a command name to its full path, searching PATH.
// We must resolve before exec since Landlock may block access to PATH dirs
// that aren't in the allowlist.
func findExecutable(name string) (string, error) {
	if strings.Contains(name, "/") {
		if _, err := os.Stat(name); err != nil {
			return "", fmt.Errorf("command not found: %s", name)
		}
		return name, nil
	}
	for _, dir := range strings.Split(os.Getenv("PATH"), ":") {
		if dir == "" {
			continue
		}
		path := dir + "/" + name
		if info, err := os.Stat(path); err == nil && !info.IsDir() {
			return path, nil
		}
	}
	return "", fmt.Errorf("command not found in PATH: %s", name)
}
