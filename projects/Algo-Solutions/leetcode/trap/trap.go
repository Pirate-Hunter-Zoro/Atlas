package trap

import "algo-solutions/datastructures"

/*
Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.

Link:
https://leetcode.com/problems/trapping-rain-water/description/
*/
func trap(height []int) int {
	walls := datastructures.NewStack[[]int]()
	trapped := 0
	for i, h := range height {
		floor := 0
		for !walls.Empty() {
			lastWall := walls.Peek()
			lastHeight := lastWall[1]
			lastPosn := lastWall[0]
			trapped += (min(h, lastHeight) - floor) * (i - lastPosn - 1)
			if lastHeight <= h {
				walls.Pop()
				floor = max(floor, lastHeight)
			} else {
				break
			}
		}
		walls.Push([]int{i, h})
	}

	return trapped
}
