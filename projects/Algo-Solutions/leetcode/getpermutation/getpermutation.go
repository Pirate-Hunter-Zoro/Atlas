package getpermutation

import (
	"sort"
	"strconv"
	"strings"
)

/*
The set [1, 2, 3, ..., n] contains a total of n! unique permutations.

By listing and labeling all of the permutations in order, we get the following sequence for n = 3:
"123"
"132"
"213"
"231"
"312"
"321"

Given n and k, return the kth permutation sequence.

Link:
https://leetcode.com/problems/permutation-sequence/description/
*/
func getPermutation(n int, k int) string {
	// Let us think of k as the number of permutations LEFT
	k = k - 1

	digitList := make([]int, n)
	for i := 1; i <= n; i++ {
		digitList[i-1] = i
	}
	factorials := make([]int, n+1)
	factorials[0] = 1
	for i := 1; i <= n; i++ {
		factorials[i] = factorials[i-1] * i
	}

	// Now perform the current permutation logic
	for k > 0 {
		// We still have permutations left
		i := -1
		factorialValue := -1
		for num := n; num >= 1; num-- {
			if factorials[num] <= k {
				i = n - num - 1
				factorialValue = factorials[num]
				break
			}
		}
		// Find the digit to switch with the i-th digit
		j := i + (k / factorialValue)
		// Switch the i-th and j-th digits
		digitList[i], digitList[j] = digitList[j], digitList[i]
		// Put the digits from i+1 to the end in increasing order
		orderedDigits := make([]int, n-i-1)
		for idx := i + 1; idx < n; idx++ {
			orderedDigits[idx-i-1] = digitList[idx]
		}
		sort.SliceStable(orderedDigits, func(i, j int) bool {
			return orderedDigits[i] < orderedDigits[j]
		})
		for idx := i + 1; idx < n; idx++ {
			digitList[idx] = orderedDigits[idx-i-1]
		}
		// Now decrease the number of permuations left
		k = k % factorialValue
	}

	var stringBuffer strings.Builder
	for _, i := range digitList {
		stringBuffer.WriteString(strconv.Itoa(i))
	}
	return stringBuffer.String()
}
