package beautifulnumbers

/*
You are given two positive integers, l and r.
A positive integer is called beautiful if the product of its digits is divisible by the sum of its digits.

Return the count of beautiful numbers between l and r, inclusive.

Link:
https://leetcode.com/problems/count-beautiful-numbers/description/?envType=problem-list-v2&envId=dynamic-programming

Inspiration:
https://leetcode.com/problems/count-beautiful-numbers/solutions/6541308/straight-forward-digit-dp-leverage-logic-of-prod-of-num-2-a-3-b-5-c-7-d-prime-factorization/
*/
func beautifulNumbers(l int, r int) int {
	// Using digit dp, we have several parameters for our state
	i := 0                      // current index of the digit we are changing
	currentDigitRestricted := 1 // whether the current digit is restricted by the main number (for the greatest-place digit, this will of course be true)
	nonZero := 0                // whether the constructed number has a non-zero prefix
	product := 1                // current running product
	sum := 0                    // current running sum

	sols := make(map[int]map[int]map[int]map[int]map[int]int)
	first := recBeautifulNumbers(digitToList(r), i, currentDigitRestricted, nonZero, product, sum, sols)
	sols = make(map[int]map[int]map[int]map[int]map[int]int)
	second := recBeautifulNumbers(digitToList(l-1), i, currentDigitRestricted, nonZero, product, sum, sols)
	return first - second
}

func digitToList(num int) []int {
	// Convert the number to a list of digits (in the same order)
	digits := []int{}
	for num > 0 {
		digits = append(digits, num%10)
		num /= 10
	}
	// Reverse the order of digits to preserve the original order
	for i, j := 0, len(digits)-1; i < j; i, j = i+1, j-1 {
		digits[i], digits[j] = digits[j], digits[i]
	}
	return digits
}

func recBeautifulNumbers(digits []int, idx int, currentDigitRestricted int, nonZero int, product int, sum int, sols map[int]map[int]map[int]map[int]map[int]int) int {
	// Check if we have already solved this problem
	if _, ok := sols[idx]; !ok {
		sols[idx] = make(map[int]map[int]map[int]map[int]int)
	}
	if _, ok := sols[idx][currentDigitRestricted]; !ok {
		sols[idx][currentDigitRestricted] = make(map[int]map[int]map[int]int)
	}
	if _, ok := sols[idx][currentDigitRestricted][nonZero]; !ok {
		sols[idx][currentDigitRestricted][nonZero] = make(map[int]map[int]int)
	}
	if _, ok := sols[idx][currentDigitRestricted][nonZero][product]; !ok {
		sols[idx][currentDigitRestricted][nonZero][product] = make(map[int]int)
	}

	if _, ok := sols[idx][currentDigitRestricted][nonZero][product][sum]; !ok {
		// Need to solve this problem
		if idx == len(digits) {
			// There are no more digits left
			if sum > 0 && product%sum == 0 {
				sols[idx][currentDigitRestricted][nonZero][product][sum] = 1
			} else {
				sols[idx][currentDigitRestricted][nonZero][product][sum] = 0
			}
		} else {
			// We can still mess with the digits
			// Note that we need to calculate an upper bound for the digit we're operating on
			sols[idx][currentDigitRestricted][nonZero][product][sum] = 0
			cap := 9
			if currentDigitRestricted == 1 {
				cap = digits[idx]
			}
			for j := 0; j <= cap; j++ {
				// Set the value of the digit at the current index to j, and then recurse to the next index position
				newProduct := product
				newNonZero := nonZero
				if nonZero == 0 {
					// First new digit starts product
					newProduct = j
				} else {
					newProduct *= j
				}
				newNonZero = nonZero
				if j > 0 {
					newNonZero = max(newNonZero, 1)
				}
				nextDigitRestricted := currentDigitRestricted
				if j < cap {
					nextDigitRestricted = 0
				}
				newSum := sum + j
				sols[idx][currentDigitRestricted][nonZero][product][sum] += recBeautifulNumbers(digits, idx+1, nextDigitRestricted, newNonZero, newProduct, newSum, sols)
			}
		}
	}
	return sols[idx][currentDigitRestricted][nonZero][product][sum]
}
