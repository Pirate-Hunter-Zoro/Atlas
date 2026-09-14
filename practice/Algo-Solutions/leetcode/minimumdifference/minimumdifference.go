package minimumdifference

import (
	"algo-solutions/datastructures"
	"math"
)

/*
You are given a 0-indexed integer array nums consisting of 3 * n elements.

You are allowed to remove any subsequence of elements of size exactly n from nums.
The remaining 2 * n elements will be divided into two equal parts:
- The first n elements belonging to the first part and their sum is sumfirst.
- The next n elements belonging to the second part and their sum is sumsecond.
- The difference in sums of the two parts is denoted as sumfirst - sumsecond.

For example, if sumfirst = 3 and sumsecond = 2, their difference is 1.
Similarly, if sumfirst = 2 and sumsecond = 3, their difference is -1.
Return the minimum difference possible between the sums of the two parts after the removal of n elements.

Link:
https://leetcode.com/problems/minimum-difference-in-sums-after-removal-of-elements/?envType=daily-question&envId=2025-07-18
*/
func minimumDifference(nums []int) int64 {
	// For starters, we're definitely going to need the sum of the entire array, as well as the left to right sum at each index
	totalSum := int64(0)
	for _, num := range nums {
		totalSum += int64(num)
	}
	// Grab the size of each "part", which is n, 1/3 of the array size
	n := len(nums) / 3
	// For a given index, what is the lowest sum you can achieve with n elements from the left?
	leftSums := make([]int64, len(nums))
	leftHeap := datastructures.NewHeap(func(a, b int64) bool {
		return a > b // Max-heap, because if we take off something, we want to take off the largest element to minimize the sum
	})
	currentSum := int64(0)
	for i := range n {
		currentSum += int64(nums[i])
		leftSums[i] = currentSum // The sum of the first n elements is just the sum of those elements
		leftHeap.Push(int64(nums[i]))
	}
	// Now we need to find the smallest n elements from the left
	for i := n; i < len(nums); i++ {
		currentSum += int64(nums[i])  // Add the current element to the sum
		leftHeap.Push(int64(nums[i])) // Push the current element to the heap
		// Now we need to remove the largest element from the heap, because we want to minimize the sum
		prevMax := leftHeap.Pop()
		currentSum -= prevMax    // Remove the largest element from the sum
		leftSums[i] = currentSum // Store the lowest possible sum of n elements up to this index
	}

	// For a given index, what is the highest sum you can achieve with n elements from the right?
	rightSums := make([]int64, len(nums))
	rightHeap := datastructures.NewHeap(func(a, b int64) bool {
		return a < b // Min-heap, because if we take off something, we want to take off the smallest element to maximize the sum
	})
	currentSum = int64(0)
	for i := len(nums) - 1; i >= len(nums)-n; i-- {
		currentSum += int64(nums[i])
		rightSums[i] = currentSum // The sum of the last n elements is just the sum of those elements
		rightHeap.Push(int64(nums[i]))
	}
	// Now we need to find the largest n elements from the right
	for i := len(nums) - n - 1; i >= 0; i-- {
		currentSum += int64(nums[i])   // Add the current element to the sum
		rightHeap.Push(int64(nums[i])) // Push the current element if it's larger than the previous min
		prevMin := rightHeap.Pop()     // Remove the smallest element from the heap
		currentSum -= prevMin          // Remove the smallest element from the sum
		rightSums[i] = currentSum      // Store the highest possible sum of n elements from this index to the end
	}

	// Now we can calculate the minimum difference between the two parts
	record := int64(math.MaxInt64)
	for i := n - 1; i <= len(leftSums)-n-1; i++ {
		record = min(record, leftSums[i]-rightSums[i+1]) // Update the record with the minimum difference found so far
	}
	return record
}
