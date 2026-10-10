package canpartition

import "sort"

/*
Given an integer array nums, return true if you can partition the array into two subsets such that the sum of the elements in both subsets is equal or false otherwise.

Link:
https://leetcode.com/problems/partition-equal-subset-sum/description/?envType=daily-question&envId=2025-04-07
*/
func canPartition(nums []int) bool {
	// First see if the sum of the numbers is even
	sum := 0
	for _, num := range nums {
		sum += num
	}
	if sum%2 != 0 {
		return false
	}
	// Now we need to find a subset of the numbers that add up to sum/2
	target := sum / 2
	// This just became a knapsack problem
	sort.SliceStable(nums, func(i, j int) bool {
		return nums[i] < nums[j]
	})
	sols := make([][]bool, len(nums)+1)
	for i := range len(nums) + 1 {
		sols[i] = make([]bool, target+1)
		for j := range target + 1 {
			sols[i][j] = false
		}
		sols[i][0] = true // We can always make a sum of 0 by picking nothing
	}
	// Now we solve the problem (bottum up approach)
	for allowedNums := 1; allowedNums <= len(nums); allowedNums++ {
		for targetSum := 1; targetSum <= target; targetSum++ {
			if nums[allowedNums-1] > targetSum {
				// We cannot use this number
				sols[allowedNums][targetSum] = sols[allowedNums-1][targetSum]
			} else {
				// We can either use this number or not
				sols[allowedNums][targetSum] = sols[allowedNums-1][targetSum] || sols[allowedNums-1][targetSum-nums[allowedNums-1]]
			}
		}
	}

	return sols[len(nums)][target]
}
