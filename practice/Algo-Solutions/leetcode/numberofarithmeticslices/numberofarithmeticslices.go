package numberofarithmeticslices

import "algo-solutions/helpermath"

/*
Given an integer array nums, return the number of all the arithmetic subsequences of nums.

A sequence of numbers is called arithmetic if it consists of at least three elements and if the difference between any two consecutive elements is the same.

For example, [1, 3, 5, 7, 9], [7, 7, 7, 7], and [3, -1, -5, -9] are arithmetic sequences.
For example, [1, 1, 2, 5, 7] is not an arithmetic sequence.
A subsequence of an array is a sequence that can be formed by removing some elements (possibly none) of the array.

For example, [2,5,10] is a subsequence of [1,2,1,2,4,1,5,10].
The test cases are generated so that the answer fits in 32-bit integer.

Link:
https://leetcode.com/problems/arithmetic-slices-ii-subsequence/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func numberOfArithmeticSlices(nums []int) int {
	// Answer the question - at this index with this difference, how many subsequences are there that end here?
	sols := make([]map[int]int, len(nums))
	total := 0
	for end := range nums {
		sols[end] = make(map[int]int)
		for start := range end {
			diff := nums[end] - nums[start]
			if _, ok := sols[end][diff]; !ok {
				// We haven't seen this difference before - initialize it
				sols[end][diff] = 0
			}
			if _, ok := sols[start][diff]; ok {
				// We can extend all the subsequences that end at start with this difference by tacking on nums[end]
				sols[end][diff] += sols[start][diff]
			}
			// We can also count the subsequence [nums[start], nums[end]] as a new subsequence
			sols[end][diff]++
		}
		for _, v := range sols[end] {
			// We can count the subsequence [nums[end]] as a new subsequence
			total += v
		}
	}

	// Subtract all the subsequences of length 2 from the total since we counted those too
	return total - helpermath.NewChooseCalculator().Choose(len(nums), 2)
}
