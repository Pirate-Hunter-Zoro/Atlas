package numberofpaths

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
You are given a 0-indexed m x n integer matrix grid and an integer k.
You are currently at position (0, 0) and you want to reach position (m - 1, n - 1) moving only down or right.

Return the number of paths where the sum of the elements on the path is divisible by k.
Since the answer may be very large, return it modulo 10⁹ + 7.

Link:
https://leetcode.com/problems/paths-in-matrix-whose-sum-is-divisible-by-k/description/
*/
func numberOfPaths(grid [][]int, k int) int {
	// For every number from 0 through k-1, and any space on the grid, we need to be able to answer the number of paths that sum to that number and end at that space
	var solve func(target int, spot int) int
	m := len(grid)
	n := len(grid[0])
	sols := make([]int, k*m*n)
	for i := range len(sols) {
		sols[i] = -1
	}
	solve = func(target int, spot int) int {
		r := int(spot / n)
		c := spot % n
		if sols[target*m*n+spot] == -1 {
			// Need to solve this problem

			// Base case - first cell
			if r == 0 && c == 0 {
				if grid[r][c]%k == target {
					sols[target*m*n+spot] = 1
				} else {
					sols[target*m*n+spot] = 0
				}
			} else {
				// Non base case
				newTarget := ((target % k) + k - (grid[r][c] % k)) % k
				// Look at two preceding possible neighbor spots and see how they could have helped
				count := 0
				if c > 0 {
					// Can look left
					count = helpermath.ModAdd(count, solve(newTarget, spot-1), leetcode.MOD)
				}
				if r > 0 {
					// Can look up
					count = helpermath.ModAdd(count, solve(newTarget, spot-n), leetcode.MOD)
				}
				sols[target*m*n+spot] = count
			}

		}
		return sols[target*m*n+spot]
	}
	return solve(0, m*n-1)
}
