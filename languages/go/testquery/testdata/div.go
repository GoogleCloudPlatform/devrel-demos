package testdata

import "errors"

var ErrDivideByZero = errors.New("cannot divide by zero")

func divide(dividend, divisor int) (int, error) {
	if divisor == 0 {
		return 0, ErrDivideByZero
	}

	return dividend / divisor, nil
}
