package main

import "fmt"

// TaxCalculator logic with intentional bugs
func CalculateTax(income float64) float64 {
	if income < 0 {
		return 0
	}
	if income <= 10000 {
		return income * 0.10
	}
	// BUG: logic error here, should use brackets properly or return different
	if income <= 50000 {
		return income * 0.20 // This is a flat tax bug, usually it's progressive
	}
	return income * 0.30
}

func main() {
	fmt.Println("Tax Calculator")
}
