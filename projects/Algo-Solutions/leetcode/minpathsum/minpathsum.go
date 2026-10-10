package minpathsum

/*
Given a m x n grid filled with non-negative numbers, find a path from top left to bottom right, which minimizes the sum of all numbers along its path.

Note: You can only move either down or right at any point in time.

Link:
https://leetcode.com/problems/minimum-path-sum/description/
*/
func minPathSum(grid [][]int) int {
	// DP fillup for first row
	m := len(grid)
	n := len(grid[0])
	curr := make([]int, n)
	for i := range n {
		curr[i] = grid[0][i]
		if i > 0 {
			curr[i] += curr[i-1]
		}
	}

	next := make([]int, n)
	for i := range m - 1 {
		for j := range n {
			next[j] = curr[j] + grid[i+1][j] // The index of our current solution row is one above i
			if j > 0 {
				next[j] = min(next[j], next[j-1]+grid[i+1][j])
			}
		}
		curr = next
	}

	return curr[n-1]
}
