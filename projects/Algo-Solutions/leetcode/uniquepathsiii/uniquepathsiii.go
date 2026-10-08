package uniquepathsiii

/*
You are given an m x n integer array grid where grid[i][j] could be:
- 1 representing the starting square. There is exactly one starting square.
- 2 representing the ending square. There is exactly one ending square.
- 0 representing empty squares we can walk over.
- -1 representing obstacles that we cannot walk over.

Return the number of 4-directional walks from the starting square to the ending square, that walk over every non-obstacle square exactly once.

Link:
https://leetcode.com/problems/unique-paths-iii/description/
*/
func uniquePathsIII(grid [][]int) int {
	start := []int{-1, -1}
	end := []int{-1, -1}
	targetSteps := 1 // Number of steps needed for a valid walk - add to this as we find empty cells
	for i := range grid {
		for j := range grid[i] {
			switch grid[i][j] {
			case 1:
				start[0] = i
				start[1] = j
			case 2:
				end[0] = i
				end[1] = j
			case 0:
				targetSteps += 1
			}
		}
	}

	// Solve the problem
	var solve func(i, j, steps int) int
	solve = func(i, j, steps int) int { // Given what we've travelled and where we are, how may Hamiltonian Paths can we count from here?
		if i < 0 || j < 0 || i >= len(grid) || j >= len(grid[0]) || grid[i][j] == -1 {
			// Out of bounds or an obstacle
			return 0
		} else if i == end[0] && j == end[1] {
			// At the goal
			if steps == targetSteps {
				return 1
			} else {
				return 0
			}
		} else {
			// At the start or on an open space
			oldMark := grid[i][j]
			grid[i][j] = -1 // Mark as visited
			// Explore neighbors
			total := 0
			total += solve(i+1, j, steps+1)
			total += solve(i-1, j, steps+1)
			total += solve(i, j+1, steps+1)
			total += solve(i, j-1, steps+1)
			grid[i][j] = oldMark // Remove visited mark
			return total
		}
	}

	return solve(start[0], start[1], 0)
}
