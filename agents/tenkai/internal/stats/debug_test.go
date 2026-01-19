package stats

import (
	"math/rand"
	"time"
)

func generateData(n int, mean, stdDev float64) []float64 {
	rand.Seed(time.Now().UnixNano())
	data := make([]float64, n)
	for i := 0; i < n; i++ {
		data[i] = rand.NormFloat64()*stdDev + mean
	}
	return data
}
