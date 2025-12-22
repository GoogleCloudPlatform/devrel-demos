package stats

import (
	"math"
)

// Mean calculates the average of a slice of float64.
func Mean(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	var sum float64
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

// Variance calculates the variance of a slice of float64.
func Variance(data []float64) float64 {
	if len(data) < 2 {
		return 0
	}
	mean := Mean(data)
	var sum float64
	for _, v := range data {
		diff := v - mean
		sum += diff * diff
	}
	return sum / float64(len(data)-1)
}

// WelchTTest calculates the p-value for the difference between two means
// using Welch's t-test (unequal variances).
func WelchTTest(data1, data2 []float64) float64 {
	n1 := float64(len(data1))
	n2 := float64(len(data2))

	if n1 < 2 || n2 < 2 {
		return 1.0 // Not enough data
	}

	m1 := Mean(data1)
	m2 := Mean(data2)
	v1 := Variance(data1)
	v2 := Variance(data2)

	// Welch-Satterthwaite equation for degrees of freedom
	se1 := v1 / n1
	se2 := v2 / n2
	se := math.Sqrt(se1 + se2)

	if se == 0 {
		if m1 == m2 {
			return 1.0
		}
		return 0.0
	}

	t := math.Abs(m1-m2) / se
	df := MathPow(se1+se2, 2) / (MathPow(se1, 2)/(n1-1) + MathPow(se2, 2)/(n2-1))

	// Approximate p-value from t and df
	return StudentTPValue(t, df)
}

func MathPow(a, b float64) float64 {
	return math.Pow(a, b)
}

// StudentTPValue approximates the two-tailed p-value for Student's T distribution.
func StudentTPValue(t, df float64) float64 {
	if df > 100 {
		return 2 * (1 - normalCDF(t))
	}
	return 2 * (1 - normalCDF(t*math.Sqrt(1-1/(4*df))))
}

func normalCDF(x float64) float64 {
	return 0.5 * (1 + math.Erf(x/math.Sqrt(2)))
}

// FisherExactTest calculates the p-value for a 2x2 contingency table.
func FisherExactTest(a, b, c, d int) float64 {
	n := a + b + c + d
	if n == 0 {
		return 1.0
	}

	logP := logHypergeometric(a, a+b, a+c, n)
	observedP := math.Exp(logP)

	pValue := 0.0
	minA := 0
	if (a+b)+(a+c) > n {
		minA = (a + b) + (a + c) - n
	}
	maxA := a + b
	if a+c < maxA {
		maxA = a + c
	}

	for i := minA; i <= maxA; i++ {
		lp := logHypergeometric(i, a+b, a+c, n)
		p := math.Exp(lp)
		if p <= observedP*1.00000001 {
			pValue += p
		}
	}

	if pValue > 1.0 {
		return 1.0
	}
	return pValue
}

func logHypergeometric(k, n, K, N int) float64 {
	return logBinomial(K, k) + logBinomial(N-K, n-k) - logBinomial(N, n)
}

func logBinomial(n, k int) float64 {
	if k < 0 || k > n {
		return -1e100
	}
	if k == 0 || k == n {
		return 0
	}
	if k > n/2 {
		k = n - k
	}
	return logFactorial(n) - logFactorial(k) - logFactorial(n-k)
}

var factorialCache []float64

func logFactorial(n int) float64 {
	if n < 0 {
		return -1e100
	}
	if n <= 1 {
		return 0
	}
	if len(factorialCache) > n && factorialCache[n] != 0 {
		return factorialCache[n]
	}
	if len(factorialCache) <= n {
		newCache := make([]float64, n+1)
		copy(newCache, factorialCache)
		factorialCache = newCache
	}
	if n < 100 {
		res := 0.0
		for i := 2; i <= n; i++ {
			res += math.Log(float64(i))
		}
		factorialCache[n] = res
		return res
	}
	res := float64(n)*math.Log(float64(n)) - float64(n) + 0.5*math.Log(2*math.Pi*float64(n))
	factorialCache[n] = res
	return res
}
