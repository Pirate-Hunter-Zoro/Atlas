package uniquepathswithobstacles

/*
You are given an m x n integer array grid.
There is a robot initially located at the top-left corner (i.e., grid[0][0]).
The robot tries to move to the bottom-right corner (i.e., grid[m - 1][n - 1]).
The robot can only move either down or right at any point in time.

An obstacle and space are marked as 1 or 0 respectively in grid.
A path that the robot takes cannot include any square that is an obstacle.

Return the number of possible unique paths that the robot can take to reach the bottom-right corner.

The testcases are generated so that the answer will be less than or equal to 2 * 10⁹.

Link:
https://leetcode.com/problems/unique-paths-ii/description/
*/
func uniquePathsWithObstacles(obstacleGrid [][]int) int {
	// Array for counts from from above
	prev := make([]int, len(obstacleGrid[0]))
	if obstacleGrid[0][0] == 0 {
		prev[0] = 1
	}
	// Array for counts of current row
	curr := make([]int, len(obstacleGrid[0]))
	for i := range len(obstacleGrid) {
		for j := range len(curr) {
			if obstacleGrid[i][j] == 0 {
				curr[j] = prev[j]
				if j > 0 {
					curr[j] += curr[j-1]
				}
			}
		}
		prev = curr
		curr = make([]int, len(prev))
	}

	return prev[len(prev)-1]
}
