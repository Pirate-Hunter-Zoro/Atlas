package minimumtime

/*
You are given an integer n, which indicates that there are n courses labeled from 1 to n.
You are also given a 2D integer array relations where relations[j] = [prevCourseⱼ, nextCourseⱼ] denotes that course prevCourseⱼ has to be completed before course nextCourseⱼ (prerequisite relationship).
Furthermore, you are given a 0-indexed integer array time where time[i] denotes how many months it takes to complete the (i+1)th course.

You must find the minimum number of months needed to complete all the courses following these rules:
- You may start taking a course at any time if the prerequisites are met.
- Any number of courses can be taken at the same time.
- Return the minimum number of months needed to complete all the courses.

Note: The test cases are generated such that it is possible to complete every course (i.e., the graph is a directed acyclic graph).

Link:
https://leetcode.com/problems/parallel-courses-iii/description/
*/
func minimumTime(n int, relations [][]int, time []int) int {
	// Keep track of which courses need to follow which other courses
	mustFollow := make([][]int, n)
	for i := range n {
		mustFollow[i] = []int{}
	}
	for _, r := range relations {
		// The relations are 1-indexed
		before, after := r[0]-1, r[1]-1
		mustFollow[after] = append(mustFollow[after], before)
	}

	// Declare helper function to find the earliest time you could complete a course by
	var earliestTime func(i int) int
	var earliestTimes []int
	earliestTimes = make([]int, n)
	for i := range n {
		earliestTimes[i] = -1
	}
	earliestTime = func(i int) int {
		if earliestTimes[i] == -1 {
			// Need to solve this problem
			record := time[i]
			for _, completeBefore := range mustFollow[i] {
				// Find the earliest time each of the parents can be completed.
				// What if two of these "parent" courses also have the relationship that one must be completed before the other?
				// The recursion should still work out.
				record = max(record, earliestTime(completeBefore)+time[i])
			}
			earliestTimes[i] = record
		}
		return earliestTimes[i]
	}

	// Now go through all courses and simply find the latest time they can be completed
	record := 0
	for i := range n {
		record = max(record, earliestTime(i))
	}
	return record
}
