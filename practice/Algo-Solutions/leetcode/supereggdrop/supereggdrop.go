package supereggdrop

import (
	"algo-solutions/helpermath"
	"math"
)

/*
You are given n identical eggs and you have access to a building with k floors labeled from 1 to n.

You know that there exists a floor f where 0 <= f <= n such that any egg dropped at a floor higher than f will break, and any egg dropped at or below floor f will not break.

Each move, you may take an unbroken egg and drop it from any floor x (where 1 <= x <= n).
If the egg breaks, you can no longer use it.
However, if the egg does not break, you may reuse it in future moves.

Return the minimum number of moves that you need to determine with certainty what the value of f is.

Link: https://leetcode.com/problems/super-egg-drop/

Inpsiration:
https://brilliant.org/wiki/egg-dropping/
*/
func superEggDrop(n int, k int) int {
	// We need to be able to cover n floors...
	// How many drops will it take to cover k floors with n eggs? Binary search...
	left := 1
	right := k
	chooser := helpermath.NewChooseCalculator()
	for left < right {
		mid := int((left + right) / 2)
		numFloorsCovered := 0
		// Calculate the number of floors covered given that we have 'mid' drops and n eggs
		for i := 1; i <= n; i++ {
			// From the article
			numFloorsCovered += chooser.Choose(mid, i)
			if numFloorsCovered < 0 { // avoid integer overflow
				numFloorsCovered = int(math.MaxInt)
				break
			}
		}
		if numFloorsCovered < k {
			// Need more drops
			left = mid + 1
		} else if numFloorsCovered > k {
			// Try using less drops
			right = mid
		} else {
			return mid
		}
	}

	return left
}
