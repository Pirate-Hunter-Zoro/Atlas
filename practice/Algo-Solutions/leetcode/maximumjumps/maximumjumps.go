package maximumjumps

import "math"

/*
You are given a 0-indexed array nums of n integers and an integer target.
You are initially positioned at index 0.
In one step, you can jump from index i to any index j such that:

	0 <= i < j < n
	-target <= nums[j] - nums[i] <= target

Return the maximum number of jumps you can make to reach index n - 1.

If there is no way to reach index n - 1, return -1.

Link:
http://leetcode.com/problems/maximum-number-of-jumps-to-reach-the-last-index/?envType=daily-question&envId=2026-05-10
*/
func maximumJumps(nums []int, target int) int {
	sols := make([]int, len(nums)) // sols[i] stores the answer to our question at position i
	for i := len(sols) - 2; i >= 0; i-- {
		// Find all next possible places to jump
		for j := i + 1; j < len(nums); j++ {
			if int(math.Abs(float64(nums[i]-nums[j]))) <= target {
				// We can jump there
				sols[i] = max(sols[i], 1+sols[j])
			}
		}
		if sols[i] == 0 {
			// We couldn't jump anywhere
			sols[i] = -1
		}
	}
	return sols[0]
}
