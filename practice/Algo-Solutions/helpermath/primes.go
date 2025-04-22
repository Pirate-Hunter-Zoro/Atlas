package helpermath

import "maps"

// GeneratePrimes returns a slice of all primes ≤ n
func GeneratePrimes(n int) []int {
	if n < 2 {
		return []int{}
	}

	isPrime := make([]bool, n+1)
	// Assume all numbers are prime
	for i := range isPrime {
		isPrime[i] = true
	}
	// 0 and 1 are not prime
	isPrime[0], isPrime[1] = false, false

	// Then for all numbers that are multiples of primes, mark them as non-prime
	for i := 2; i*i <= n; i++ {
		// Start at i*i, since all smaller multiples of i have already been marked
		if isPrime[i] {
			for j := i * i; j <= n; j += i {
				isPrime[j] = false
			}
		}
	}

	// Now generate a list of all primes
	primes := []int{}
	for i := 2; i <= n; i++ {
		if isPrime[i] {
			primes = append(primes, i)
		}
	}
	return primes
}

// Method to return all prime factors (and their powers) of a number given the list of primes we can choose from (for efficiency don't compute this within the function)
func PrimeFactors(n int, prime_list []int) map[int]int {
	return recPrimeFactors(n, make(map[int]map[int]int), prime_list)
}
// Helper method for the above
func recPrimeFactors(n int, memo map[int]map[int]int, prime_list []int) map[int]int {
	if _, ok := memo[n]; !ok {
		// Need to solve this problem
		if n < 2 {
			memo[n] = make(map[int]int)
		} else {
			memo[n] = make(map[int]int)
			for _, p := range prime_list {
				// Once we find a prime divisor, we can stop and go to a subproblem
				if n % p == 0 {
					sub_sols := recPrimeFactors(n/p, memo, prime_list)
					// Copy the solution for this number with an extra count of p
					maps.Copy(memo[n], sub_sols)
					// If the key doesn't exist, this will initialize its value to 1
					memo[n][p]++
					break
				}
			}
		}
	}
	return memo[n]
}