package containsnearbyalmostduplicate

import (
	"math"
	"sort"
)

/*
You are given an integer array nums and two integers indexDiff and valueDiff.

Find a pair of indices (i, j) such that:
- i != j,
- abs(i - j) <= indexDiff.
- abs(nums[i] - nums[j]) <= valueDiff, and

Return true if such pair exists or false otherwise.

Link:
https://leetcode.com/problems/contains-duplicate-iii/description/

Inspiration:
https://leetcode.com/problems/contains-duplicate-iii/solutions/824578/c-o-n-time-complexity-explained-buckets-o-k-space-complexity/
*/
func containsNearbyAlmostDuplicate(nums []int, indexDiff int, valueDiff int) bool {
	// The following logic will only work if all values are positive
	lowestVal := math.MaxInt
	for _, v := range nums {
		lowestVal = min(lowestVal, v)
	}
	// Now shift all values by abs(lowestVal) so that all values are positive
	for i := range nums {
		nums[i] -= lowestVal
	}

	// Put the numbers in buckets based on their division values by valueDiff+1 (also store the index)
	buckets := make(map[int][][]int)
	for i, v := range nums {
		q := v / (valueDiff + 1)
		_, ok := buckets[q]
		if !ok {
			buckets[q] = [][]int{}
		}
		buckets[q] = append(buckets[q], []int{v, i})
	}
	// Note all the buckets already sorted based on indices
	for _, bucket := range buckets {
		for i := range len(bucket) - 1 {
			j := i + 1
			// Look at consecutive elements in the bucket
			if bucket[j][1]-bucket[i][1] <= indexDiff {
				return true
			}
		}
	}

	// We also need to check neighboring buckets - last element of first bucket and first element of second bucket
	bucketKeys := []int{}
	for k := range buckets {
		bucketKeys = append(bucketKeys, k)
	}
	sort.SliceStable(bucketKeys, func(i, j int) bool {
		return bucketKeys[i] < bucketKeys[j]
	})
	for i := range len(bucketKeys) - 1 {
		bucket1 := buckets[bucketKeys[i]]
		bucket2 := buckets[bucketKeys[i+1]]
		if (bucket2[0][1]-bucket1[len(bucket1)-1][1] <= indexDiff) && (bucket2[0][0]-bucket1[len(bucket1)-1][0] <= valueDiff) {
			return true
		}
	}

	return false
}
