package splitarray

/*
Given an integer array nums and an integer k, split nums into k non-empty subarrays such that the largest sum of any subarray is minimized.

Return the minimized largest sum of the split.

A subarray is a contiguous part of the array.

Link: https://leetcode.com/problems/split-array-largest-sum/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func splitArray(nums []int, k int) int {
	// We are going to binary search for the smallest possible maximum sum
	left := 0
	right := 0
	for _, v := range nums {
		right += v
	}
	for left < right {
		mid := (left + right) / 2
		if canSplit(nums, k, mid) {
			right = mid
		} else {
			left = mid + 1
		}
	}
	return left
}

func canSplit(nums []int, k int, maxSum int) bool {
	// We need to see if we can split the array into k subarrays such that the maximum sum of any subarray is less than or equal to maxSum
	count := 1
	sum := 0
	// As we build our sliding window, make sure we don't exceed the maximum sum - if that requires more than k splits, then we're out of luck
	for _, v := range nums {
		if sum+v > maxSum {
			count++
			sum = v
		} else {
			sum += v
		}
		if sum > maxSum {
			// A single value is too large to fit in the maximum sum
			return false
		}
	}
	return count <= k
}
