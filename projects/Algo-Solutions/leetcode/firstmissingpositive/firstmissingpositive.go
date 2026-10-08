package firstmissingpositive

import "math"

/*
Given an unsorted integer array nums.
Return the smallest positive integer that is not present in nums.

You must implement an algorithm that runs in O(n) time and uses O(1) auxiliary space.
Link: https://leetcode.com/problems/first-missing-positive/
*/
func firstMissingPositive(nums []int) int {
	// The LeetCode editorial was insanely helpful...
	n := len(nums)
	// Note that the lowest missing positive integer can only be in {1,...,n+1}
	oneMissing := true
	// Mark all zero or negative elements as 1 instead - but while we're doing that make sure 1 isn't the lowest positive missing - if it is return it
	for i, v := range nums {
		if v == 1 {
			oneMissing = false
		} else if v > n || v <= 0 {
			nums[i] = 1
		}
	}
	if oneMissing {
		return 1
	} else {
		// Loop through the array once again
		for _, v := range nums {
			// Mark position v in the array as seen by making it negative
			idx := int(math.Abs(float64(v))) - 1
			nums[idx] = -int(math.Abs(float64(nums[idx])))
		}
		// Now go through the list again - the first index that is not negative corresponds with the lowest missing positive value
		for i := 0; i < len(nums); i++ {
			if nums[i] > 0 {
				// Never seen
				return i + 1
			}
		}
		// Only remaining possibility
		return n + 1
	}
}
