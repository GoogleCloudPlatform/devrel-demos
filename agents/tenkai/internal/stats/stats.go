package stats

import (
	"math"
	"sort"
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

	if n1 < 5 || n2 < 5 {
		return 1.0 // Not enough data for reliable Normal approximation
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

// Rank computes the fractional rank of the data.
// Ties are assigned the average rank of the tied values.
func Rank(data []float64) []float64 {
	type item struct {
		val   float64
		index int
	}
	items := make([]item, len(data))
	for i, v := range data {
		items[i] = item{val: v, index: i}
	}

	sort.Slice(items, func(i, j int) bool {
		return items[i].val < items[j].val
	})

	ranks := make([]float64, len(data))
	for i := 0; i < len(items); {
		j := i + 1
		for j < len(items) && items[j].val == items[i].val {
			j++
		}
		// items[i...j-1] are ties
		rankSum := 0.0
		for k := i; k < j; k++ {
			rankSum += float64(k + 1)
		}
		avgRank := rankSum / float64(j-i)
		for k := i; k < j; k++ {
			ranks[items[k].index] = avgRank
		}
		i = j
	}
	return ranks
}

// MannWhitneyU calculates the p-value for the Mann-Whitney U test (two-sided).
// It tests the null hypothesis that the distributions of sample1 and sample2 are the same.
func MannWhitneyU(sample1, sample2 []float64) float64 {
	n1 := float64(len(sample1))
	n2 := float64(len(sample2))
	if n1 == 0 || n2 == 0 {
		return 1.0
	}

	all := append([]float64{}, sample1...)
	all = append(all, sample2...)
	ranks := Rank(all)

	r1 := 0.0
	for i := 0; i < int(n1); i++ {
		r1 += ranks[i]
	}

	u1 := r1 - n1*(n1+1)/2.0
	u2 := n1*n2 - u1

	u := math.Min(u1, u2)

	// Normal approximation for large samples (or if we just want a simple implementation)
	// For small samples, exact tables are ideal, but normal approx is standard for dev tools.
	mu := n1 * n2 / 2.0

	// Tie correction for standard deviation
	// sigma = sqrt( (n1*n2/12) * ( (N^3 - N - sum(t^3 - t)) / (N*(N-1)) ) )
	// Simplified without tie correction for now:
	sigma := math.Sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)

	if sigma == 0 {
		return 1.0
	}

	z := (u - mu) / sigma
	// Continuity correction check could go here

	// P-value (two-tailed)
	return 2.0 * (1.0 - normalCDF(math.Abs(z)))
}

// SpearmanCorrelation calculates the Spearman's rank correlation coefficient.
func SpearmanCorrelation(x, y []float64) float64 {
	if len(x) != len(y) || len(x) < 2 {
		return 0.0
	}

	rx := Rank(x)
	ry := Rank(y)

	mx := Mean(rx)
	my := Mean(ry)

	num := 0.0
	denX := 0.0
	denY := 0.0

	for i := 0; i < len(x); i++ {
		dx := rx[i] - mx
		dy := ry[i] - my
		num += dx * dy
		denX += dx * dx
		denY += dy * dy
	}

	if denX == 0 || denY == 0 {
		return 0.0
	}

	return num / math.Sqrt(denX*denY)
}
