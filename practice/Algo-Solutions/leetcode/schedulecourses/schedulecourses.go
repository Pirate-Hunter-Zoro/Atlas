package schedulecourses

import (
	"algo-solutions/datastructures"
	"sort"
)

/*
There are n different online courses numbered from 1 to n.
You are given an array courses where courses[i] = [durationᵢ, lastDayᵢ] indicate that the ith course should be taken continuously for durationᵢ days and must be finished before or on lastDayᵢ.

You will start on the 1st day and you cannot take two or more courses simultaneously.

Return the maximum number of courses that you can take.

Link:
https://leetcode.com/problems/course-schedule-iii/description/
*/
func scheduleCourse(courses [][]int) int {
	// Sort courses by deadline
	sort.SliceStable(courses, func(i, j int) bool {
		return courses[i][1] < courses[j][1]
	})

	// Put the courses in a heap sorted by course length, keeping track of elapsed time
	courseHeap := datastructures.NewHeap(func(first []int, second []int) bool {
		return first[0] >= second[0]
	})
	elapsedTime := 0
	for _, course := range courses {
		if course[1] >= elapsedTime+course[0] {
			// We can take the course - for now just try to take it
			elapsedTime += course[0]
			courseHeap.Push(course)
		} else {
			if courseHeap.Size() > 0 {
				longestTakenCourse := courseHeap.Peek()
				elapsedIfRemove := elapsedTime - longestTakenCourse[0]
				if elapsedIfRemove+course[0] <= course[1] && longestTakenCourse[0] > course[0] {
					// Removing this old course would let us take this next course, AND this next course takes less time
					// So do it
					courseHeap.Pop()
					elapsedTime = elapsedIfRemove + course[0]
					courseHeap.Push(course)
				}
			}
		}
	}

	return courseHeap.Size()
}
