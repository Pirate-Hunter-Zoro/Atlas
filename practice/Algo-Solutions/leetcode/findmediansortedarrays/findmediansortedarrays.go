package findmediansortedarrays

import "math"

/*
Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays.

The overall run time complexity should be O(log (m+n)).

Link:
https://leetcode.com/problems/median-of-two-sorted-arrays/description/
*/
func findMedianSortedArrays(nums1 []int, nums2 []int) float64 {
	// Dummy cases
	var findMedian func(nums []int) float64
	findMedian = func(nums []int) float64 {
		if len(nums)%2 == 1 {
			// Odd
			return float64(nums[int(len(nums)/2)])
		} else {
			// Even
			return float64(nums[int(len(nums)/2)-1]+nums[int(len(nums)/2)]) / 2
		}
	}
	if len(nums1) == 0 {
		return findMedian(nums2)
	} else if len(nums2) == 0 {
		return findMedian(nums1)
	}

	if len(nums1) > len(nums2) {
		nums1, nums2 = nums2, nums1
	}
	m := len(nums1)
	n := len(nums2)
	// Consider a left partition of the first array, and a left partition of the second array
	totalLeft := (m + n + 1) / 2 // Together they must total this many elements
	// Binary search on smaller array
	low := -1          // Lowest possible pivot (last index of the partition which goes into totalLeft) for smaller array - in this case no values are taken from the first array
	high := m          // One more than the highest possible pivot for smaller array
	var pivotNums1 int // Pivot index for the first array
	var pivotNums2 int // Pivot index for the second array
	var maxLeft1 int   // Value at the pivot index in first array
	var minRight1 int  // Value just right of pivot index in first array (NOT included in totalLeft)
	var maxLeft2 int   // Value at the pivot index in second array
	var minRight2 int  // Value just right of pivot index in second array (NOT included in totalLeft)
	for low < high {
		pivotNums1 = int(math.Floor(float64((low + high)) / 2)) // Guess for pivot index in first array
		pivotNums2 = totalLeft - pivotNums1 - 1 - 1             // Resulting pivot index in second array

		// Find the values associated with these two pivots
		if pivotNums1 == -1 {
			maxLeft1 = math.MinInt // No values from the first array included
		} else {
			maxLeft1 = nums1[pivotNums1]
		}
		if pivotNums1 == m-1 {
			minRight1 = math.MaxInt // All values from the first array included
		} else {
			minRight1 = nums1[pivotNums1+1]
		}
		if pivotNums2 == -1 {
			maxLeft2 = math.MinInt // No values from the second array included
		} else {
			maxLeft2 = nums2[pivotNums2]
		}
		if pivotNums2 == n-1 {
			minRight2 = math.MaxInt // All values from the second array included
		} else {
			minRight2 = nums2[pivotNums2+1]
		}

		// Check to see if we need to raise or lower the left array's pivot
		if maxLeft1 <= minRight2 && maxLeft2 <= minRight1 {
			// These pivots work and we have exactly half the elements which are the lower half IN the left half given these two partitions
			if (m+n)%2 == 1 {
				// Odd
				return float64(max(maxLeft1, maxLeft2))
			} else {
				// Even - average of last value in left half and first value in right half
				return float64(max(maxLeft1, maxLeft2)+min(minRight1, minRight2)) / float64(2)
			}
		} else if maxLeft1 <= minRight2 {
			// Array 1 has too small of a pivot - minRight1 is too small
			low = pivotNums1 + 1
		} else {
			// Vice versa - minRight2 is too small
			high = pivotNums1
		}
	}
	// Should never reach here
	return -1
}
