package service

import "time"

func CheckStuckEvaluationsForTest(svc HackathonService, timeout time.Duration) {
	svc.(*hackathonService).checkStuckEvaluations(timeout)
}
