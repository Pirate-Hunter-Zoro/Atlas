package findorder

import "algo-solutions/datastructures"

/*
There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1.
You are given an array prerequisites where prerequisites[i] = [aᵢ, bᵢ] indicates that you must take course bᵢ first if you want to take course aᵢ.

For example, the pair [0, 1], indicates that to take course 0 you have to first take course 1.
Return the ordering of courses you should take to finish all courses.
If there are many valid answers, return any of them.
If it is impossible to finish all courses, return an empty array.

Link:
https://leetcode.com/problems/course-schedule-ii/description/?envType=problem-list-v2&envId=topological-sort
*/
func findOrder(numCourses int, prerequisites [][]int) []int {
	// For each class, what are the classes it is a requirement for?
	prereqFor := make([][]int, numCourses)
	for i := range numCourses {
		prereqFor[i] = []int{}
	}
	inDegree := make([]int, numCourses)
	for _, required := range prerequisites {
		prereqFor[required[1]] = append(prereqFor[required[1]], required[0])
		inDegree[required[0]]++
	}

	// Use a queue to take courses, and move on to courses with in-degree zero
	taken := []int{}
	courseQueue := datastructures.NewQueue[int]()
	for n, d := range inDegree {
		if d == 0 {
			courseQueue.Enqueue(n)
		}
	}
	// Each couse in the queue at any point in time as in-degree zero
	for !courseQueue.Empty() {
		n := courseQueue.Size()
		for range n {
			next := courseQueue.Dequeue()
			taken = append(taken, next)
			for _, nextCourse := range prereqFor[next] {
				inDegree[nextCourse]--
				if inDegree[nextCourse] == 0 {
					// Ready to take next course
					courseQueue.Enqueue(nextCourse)
				}
			}
		}
	}

	if len(taken) == numCourses {
		return taken
	}
	return []int{}
}
