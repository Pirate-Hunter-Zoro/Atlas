package countgoodarrays

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
You are given three integers n, m, k.
A good array arr of size n is defined as follows:
- Each element in arr is in the inclusive range [1, m].
- Exactly k indices i (where 1 <= i < n) satisfy the condition arr[i - 1] == arr[i].
Return the number of good arrays that can be formed.

Since the answer may be very large, return it modulo 10⁹ + 7.

Link:
https://leetcode.com/problems/count-the-number-of-arrays-with-k-matching-adjacent-elements/description/?envType=daily-question&envId=2025-06-17
*/
func countGoodArrays(n int, m int, k int) int {
	// Edge cases
	if k == 0 && m == 1 && n > 1 {
		// No pairs of indices are equal, and only one value is allowed
		return 0
	} else if n == 1 {
		return m // If n is 1, we can just pick any of the m values
	}

	// Note that there will be n - 1 - k consecutive index pairs that are NOT equal
	// That corresponds to n - k - 1 + 1 = n - k "blocks" of consecutive equal elements
	// So how many ways can an array of size n with n - k such blocks be formed?
	blocks := n - k
	// The only constraint is that each consecutive pair of blocks must be populated with different values
	total := m // The first block can be populated with any of the m values

	// Then each subsequent block can be populated with any of the m - 1 values (since it can't be the same as the previous block)
	if blocks > 1 {
		total = helpermath.ModMul(total, helpermath.ModPow(m-1, blocks-1, leetcode.MOD), leetcode.MOD)
	}

	// Notably, THAT was only for one particular arrangement of blocks
	// n - k NONEMPTY blocks means we have n - k - 1 "dividers" to place in (n - 1) possible positions
	total = helpermath.ModMul(total, leetcode.GlobalCalculator.ChooseMod(n-1, n-k-1, leetcode.MOD), leetcode.MOD)

	return total
}
