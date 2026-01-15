package runner

import (
	"context"
	"fmt"
	"log"
	"os/exec"
	"sync"
	"time"
)

func (r *Runner) waitForCommand(cmd *exec.Cmd, streamWg *sync.WaitGroup, jobCtx context.Context, timeout time.Duration, jobID string, resultFound *bool, resultFoundMu *sync.Mutex, terminationRequested *bool) error {
	// Wait for streams to finish (pipes closed)
	streamWg.Wait()

	// If cmd is nil (Cloud Run), we rely on jobCtx or other means.
	// But in Local execution via Executor, we are NOT using this method.
	// This method is legacy/used by the old logic or we need to adapt usage.
	// With the new logic using r.executor.Execute, the blocking call happens there and returns result.
	// We no longer wait on `cmd.Wait()` here.
	// We strictly check the logic in `runner.go`.
	// `waitErr := r.waitForCommand(cmd, ...)` is called.
	// BUT `cmd` is passed as `nil` in the new refactor of `runner.go` (I passed nil there).
	// So we need to handle nil cmd.

	if cmd == nil {
		// New logic path: execution already finished (Execute returned).
		// We just interpret the context/flags.

		resultFoundMu.Lock()
		isEarlyExit := *resultFound
		resultFoundMu.Unlock()

		startGracefulExit := *terminationRequested

		if isEarlyExit {
			return nil
		}
		if startGracefulExit {
			return nil
		}
		if jobCtx.Err() == context.DeadlineExceeded {
			return fmt.Errorf("execution timeout (%v limit)", timeout)
		}

		// If none of the above, it means execution finished "naturally" (via Execute returning).
		// Any error from Execute was already captured in `res.Error`.
		// This function is mostly for updating Status based on timeout/early exit flags?
		// Actually runner.go sets res.Error from execRes.
		// So waitForCommand is redundant?
		// runner.go:
		// res.Error = execRes.Error

		return nil
	}

	// Legacy path (if cmd != nil)
	if err := cmd.Wait(); err != nil {
		// Check if early exit triggered
		resultFoundMu.Lock()
		isEarlyExit := *resultFound
		resultFoundMu.Unlock()

		startGracefulExit := *terminationRequested

		if isEarlyExit {
			// Ignore error, treat as success (result already captured)
			return nil
		} else if startGracefulExit {
			// Agent requested termination via token.
			// Treat as success even if the process was killed with SIGINT.
			// However, we must ensure we actually parsed the result.
			log.Printf("[Runner] Process %s exited locally after termination token: %v", jobID, err)
			return nil
		} else if jobCtx.Err() == context.DeadlineExceeded {
			// Check if timeout
			return fmt.Errorf("execution timeout (%v limit)", timeout)
		} else {
			return fmt.Errorf("execution failed: %w", err)
		}
	}
	return nil
}
