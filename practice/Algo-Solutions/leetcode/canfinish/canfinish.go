package canfinish

import "algo-solutions/datastructures"

/*
There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given an array prerequisites where prerequisites[i] = [ai, bi] indicates that you must take course bi first if you want to take course ai.

For example, the pair [0, 1], indicates that to take course 0 you have to first take course 1.
Return true if you can finish all courses. Otherwise, return false.

Link: https://leetcode.com/problems/course-schedule/
*/
func canFinish(numCourses int, prerequisites [][]int) bool {
	inDegree := make([]int, numCourses)
	nodesNeeded := make([][]int, numCourses) // jagged array
	for i := range numCourses {
		nodesNeeded[i] = []int{}
	}
	for _, preq := range prerequisites {
		need := preq[0]
		needed := preq[1]
		inDegree[needed]++
		nodesNeeded[need] = append(nodesNeeded[need], needed)
	}

	countInDegree0 := 0
	for i := 0; i < numCourses; i++ {
		if inDegree[i] == 0 {
			countInDegree0++
		}
	}

	nodeQueue := datastructures.NewQueue[int]()
	for i, v := range inDegree {
		if v == 0 {
			nodeQueue.Enqueue(i)
		}
	}

	for !nodeQueue.Empty() {
		next := nodeQueue.Dequeue()
		for _, neighbor := range nodesNeeded[next] {
			inDegree[neighbor]--
			if inDegree[neighbor] == 0 {
				countInDegree0++
				nodeQueue.Enqueue(neighbor)
			}
		}
	}

	return countInDegree0 == numCourses
}
