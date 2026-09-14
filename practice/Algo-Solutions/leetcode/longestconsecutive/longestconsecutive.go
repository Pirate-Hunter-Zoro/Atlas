package longestconsecutive

import "algo-solutions/datastructures"

/*
Given an unsorted array of integers nums, return the length of the longest consecutive elements sequence.

You must write an algorithm that runs in O(n) time.

Link:
https://leetcode.com/problems/longest-consecutive-sequence/description/?envType=problem-list-v2&envId=union-find
*/
func longestConsecutive(nums []int) int {
	setOfSets := datastructures.NewDisjointSet[int]()
	present := make(map[int]bool)
	for _, n := range nums {
		setOfSets.Add(n)
		present[n] = true
		_, ok := present[n-1]
		if ok {
			setOfSets.Join(n, n-1)
		}
		_, ok = present[n+1]
		if ok {
			setOfSets.Join(n, n+1)
		}
	}

	// See who has the most children - or the largest set per se - that's our longest consecutive subsequence
	record := 0
	childrenCounts := make(map[int]int)
	for n := range present {
		parent := setOfSets.GetParent(n)
		_, ok := childrenCounts[parent]
		if !ok {
			childrenCounts[parent] = 0
		}
		childrenCounts[parent]++
		record = max(record, childrenCounts[parent])
	}
	return record
}
