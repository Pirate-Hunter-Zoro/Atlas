package numberofstablearrays

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
You are given 3 positive integers zero, one, and limit.

A binary array arr is called stable if:
- The number of occurrences of 0 in arr is exactly zero.
- The number of occurrences of 1 in arr is exactly one.
- Each subarray of arr with a size greater than limit must contain both 0 and 1.

Return the total number of stable binary arrays.

Since the answer may be very large, return it modulo 10⁹ + 7.

Link:
https://leetcode.com/problems/find-all-possible-stable-binary-arrays-i/description/?envType=daily-question&envId=2026-03-09
*/
func numberOfStableArrays(zero int, one int, limit int) int {
	// A valid scheme is one in which all arrays of size limit+1 have both a 0 and a 1
	dp0 := make([][]int, zero+1) // dp0[i][j] is the number of valid schemes with i 0's and j 1's ending in a 0
	dp1 := make([][]int, zero+1) // dp1[i][j] is the number of valid schemes with i 0's and j 1's ending in a 1
	for i := range zero + 1 {
		dp0[i] = make([]int, one+1)
		dp1[i] = make([]int, one+1)
	}
	chooseCalc := helpermath.NewChooseCalculator()
	for i := range zero + 1 {
		for j := range one + 1 {
			if i == 0 || j == 0 {
				// Uniform array of all 0's or all 1's - not always feasible
				if max(i, j) <= limit {
					dp0[i][j] = 0
					dp1[i][j] = 0
					if i > 0 {
						// End in a 0
						dp0[i][j]++
					} else if j > 0 {
						// End in a 1
						dp1[i][j]++
					}
				} else {
					// Impossible - too many of all 0's or 1's given length past which we require at least one of each
					dp0[i][j] = 0
					dp1[i][j] = 0
				}
			} else if (i + j) <= limit {
				// Unlimited except for last specified digit
				dp0[i][j] = chooseCalc.ChooseMod(i+j-1, i-1, leetcode.MOD) // Last digit is set to 0, we have i-1 OTHER zeros to place in i+j-1 spots with total freedom
				dp1[i][j] = chooseCalc.ChooseMod(i+j-1, i, leetcode.MOD)   // Last digit is set to 1, we have i zeros to place in i+j-1 spots with total freedom
			} else {
				// We require a zero and a one
				dp0[i][j] = helpermath.ModAdd(dp0[i-1][j], dp1[i-1][j], leetcode.MOD) // One less 0, both previous ending digit cases
				// Correct for the cases where we had 'limit' consecutive zeros preceding
				if i > limit {
					// Note such valid sequences would have had to end in a 1, or we could not have appended limit 0's
					dp0[i][j] = helpermath.ModSub(dp0[i][j], dp1[i-1-limit][j], leetcode.MOD)
				}

				// Exact same logic for ending in a 1
				dp1[i][j] = helpermath.ModAdd(dp0[i][j-1], dp1[i][j-1], leetcode.MOD) // Again same logic but one less 1
				// Correct for the cases where we had 'limit' consecutive ones preceding
				if j > limit {
					// Again, such valid sequences would have ended in a 0, or we could not hav appended limit 1's
					dp1[i][j] = helpermath.ModSub(dp1[i][j], dp0[i][j-1-limit], leetcode.MOD)
				}
			}
		}
	}

	return helpermath.ModAdd(dp0[zero][one], dp1[zero][one], leetcode.MOD)
}
