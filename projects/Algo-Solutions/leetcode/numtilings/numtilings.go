package numtilings

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
You have two types of tiles: a 2 x 1 domino shape and a tromino shape.
You may rotate these shapes.

Given an integer n, return the number of ways to tile an 2 x n board.
Since the answer may be very large, return it modulo 10⁹ + 7.

In a tiling, every square must be covered by a tile.
Two tilings are different if and only if there are two 4-directionally adjacent cells on the board such that exactly one of the tilings has both squares occupied by a tile.

In simpler terms, imagine placing tiles on a 2×n board.
Two tilings are considered different if there's at least one pair of adjacent cells (either vertically or horizontally next to each other) where:
- In one tiling, both cells are covered by the same tile.
- In the other tiling, those same two cells are not covered by the same tile.

Link: https://leetcode.com/problems/domino-and-tromino-tiling/description/?envType=daily-question&envId=2025-05-05
*/
func numTilings(n int) int {
	sols := make([][]int, 3)
	for i := range 3 {
		sols[i] = make([]int, n+1)
	}
	return topDownNumTilings(n, 0, sols)
}

func topDownNumTilings(n int, leftSide int, sols [][]int) int {
	// leftSide = 0 => smooth left
	// leftSide = 1 => popout from top on left
	// leftSide = 2 => popout from bottom on left
	if n > 0 && sols[leftSide][n] == 0 {
		// Need to solve this problem
		if n == 1 && leftSide == 0 {
			sols[leftSide][n] = 1
		} else if n == 1 && leftSide != 0 {
			// Only one square left - you can't solve that
			sols[leftSide][n] = 0
		} else if n == 2 {
			if leftSide == 0 {
				// Two dominoes vertically or horizontally
				sols[leftSide][n] = 2
			} else {
				// You'll need a tromino to fill the gap
				sols[leftSide][n] = 1
			}
		} else {
			// Non-trivial base case
			count := 0
			switch leftSide {
			case 0:
				// Place domino vertically
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 0, sols), leetcode.MOD)
				// Place two dominoes horizontally
				count = helpermath.ModAdd(count, topDownNumTilings(n-2, 0, sols), leetcode.MOD)
				// Place a tromino hooked up
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 1, sols), leetcode.MOD)
				// Place a tromino hooked down
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 2, sols), leetcode.MOD)
			case 1:
				// Popout from top
				// Place a tromino hooked down
				count = helpermath.ModAdd(count, topDownNumTilings(n-2, 0, sols), leetcode.MOD)
				// Place a domino horizontally on bottom - yields popout from bottom
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 1, sols), leetcode.MOD)
			default:
				// Popout from bottom
				// Place a tromino hooked up
				count = helpermath.ModAdd(count, topDownNumTilings(n-2, 0, sols), leetcode.MOD)
				// Place a domino horizontally on top - yields popout from top
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 2, sols), leetcode.MOD)
			}
			sols[leftSide][n] = count
		}
	}
	return sols[leftSide][n]
}
