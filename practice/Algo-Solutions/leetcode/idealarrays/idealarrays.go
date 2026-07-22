package idealarrays

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
You are given two integers n and maxValue, which are used to describe an ideal array.

A 0-indexed integer array arr of length n is considered ideal if the following conditions hold:
- Every arr[i] is a value from 1 to maxValue, for 0 <= i < n.
- Every arr[i] is divisible by arr[i - 1], for 0 < i < n.

Return the number of distinct ideal arrays of length n.
Since the answer may be very large, return it modulo 10⁹ + 7.

Link:
https://leetcode.com/problems/count-the-number-of-ideal-arrays/description/?envType=daily-question&envId=2025-04-22

Inspiration:
https://leetcode.com/problems/count-the-number-of-ideal-arrays/editorial/?envType=daily-question&envId=2025-04-22
(And ChatGPT)
*/
func idealArrays(n int, maxValue int) int {
	// Note that each element in the array can be represented as a prime factorization
	// We need to make sure that each element's powers of prime factors are non-decreasing for each said prime factor
	// How many ways can we do this?
	// We know the exponent of each prime factor in maxValue
	// For each exponent, we need the previous exponent to be less than or equal to
	// Say the exponent value is 'e', and the array is length n
	// We need a non-decreasing sequence of length n, where the last element is e, and we allow for repeats
	// This is equivalent to the number of ways to put n indistinguishable balls into e+1 distinguishable boxes, and the exponent at each box is the cumulative sum of all balls seen at that point
	// Mathematically, this is C(n+e-1, e) - lining up spots for the balls and the dividers, and choosing e to be the balls
	// Multiply this results for ALL such prime factors of whatever value we pick last
	res := 0
	chooseCalc := helpermath.NewChooseCalculator()
	primes := helpermath.GeneratePrimes(maxValue)
	for lastV := 1; lastV <= maxValue; lastV++ {
		// Find the prime factorization of lastV
		factors := helpermath.PrimeFactors(lastV, primes)
		thisRes := 1
		for _, v := range factors {
			// v is the power of THIS prime factor - and all of maxValues prime factors can change independently
			thisRes = helpermath.ModMul(thisRes, chooseCalc.ChooseMod(n+v-1, v, leetcode.MOD), leetcode.MOD)
		}
		res = helpermath.ModAdd(res, thisRes, leetcode.MOD)
	}

	return res
}
