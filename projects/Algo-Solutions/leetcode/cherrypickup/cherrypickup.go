package cherrypickup

/*
You are given an n x n grid representing a field of cherries, each cell is one of three possible integers.
  - 0 means the cell is empty, so you can pass through,
  - 1 means the cell contains a cherry that you can pick up and pass through, or
  - -1 means the cell contains a thorn that blocks your way.

Return the maximum number of cherries you can collect by following the rules below:
  - Starting at the position (0, 0) and reaching (n - 1, n - 1) by moving right or down through valid path cells (cells with value 0 or 1).
  - After reaching (n - 1, n - 1), returning to (0, 0) by moving left or up through valid path cells.
  - When passing through a path cell containing a cherry, you pick it up, and the cell becomes an empty cell 0.
  - If there is no valid path between (0, 0) and (n - 1, n - 1), then no cherries can be collected.

Link:
https://leetcode.com/problems/cherry-pickup/description/
*/
func cherryPickup(grid [][]int) int {
	// From the editorial, consider two paths from top left to bottom right (path back is just reversed)
	// Given r1,c1, and (WLOG) r2, we can compute c2 because the two paths must have the same number of steps in a subproblem
	r := len(grid)
	c := len(grid[0])

	// DP setup
	sols := make([][][]int, r)
	for i := range r {
		sols[i] = make([][]int, c)
		for j := range c {
			sols[i][j] = make([]int, r)
			for k := range r {
				sols[i][j][k] = -2
			}
		}
	}

	var solve func(r1 int, c1 int, r2 int) int
	solve = func(r1 int, c1 int, r2 int) int {
		// Check if valid first - constant time test
		c2 := r1 + c1 - r2
		if r1 >= r || r2 >= r || c1 >= c || c2 >= c {
			return -1
		}

		if sols[r1][c1][r2] == -2 {
			// Need to solve this problem
			if grid[r1][c1] == -1 || grid[r2][c2] == -1 {
				// Must stop here
				sols[r1][c1][r2] = -1
				// Constant
			} else {
				// Need not stop
				if r1 == r-1 && r2 == r-1 && c1 == c-1 && c2 == c-1 {
					// Base case - at the end - only count its value once
					sols[r1][c1][r2] = grid[r-1][c-1]
				} else {
					// Both people can try moving right or down - that's 2x2=4 subproblems
					record := -1

					initialAmount := grid[r1][c1]
					if r1 != r2 || c1 != c2 {
						initialAmount += grid[r2][c2]
					}
					// Try both right
					if solve(r1, c1+1, r2) != -1 {
						record = max(record, initialAmount+solve(r1, c1+1, r2))
					}
					// Try both down
					if solve(r1+1, c1, r2+1) != -1 {
						record = max(record, initialAmount+solve(r1+1, c1, r2+1))
					}
					// Try first right, second down
					if solve(r1, c1+1, r2+1) != -1 {
						record = max(record, initialAmount+solve(r1, c1+1, r2+1))
					}
					// Try first down, second right
					if solve(r1+1, c1, r2) != -1 {
						record = max(record, initialAmount+solve(r1+1, c1, r2))
					}

					// Record the record
					sols[r1][c1][r2] = record
				}
			}
		}

		return sols[r1][c1][r2]
	}

	return max(0, solve(0, 0, 0))
}
