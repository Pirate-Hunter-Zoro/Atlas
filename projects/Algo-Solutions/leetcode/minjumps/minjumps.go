package minjumps

import "algo-solutions/datastructures"

/*
Given an array of integers arr, you are initially positioned at the first index of the array.

In one step you can jump from index i to index:
--> i + 1 where: i + 1 < arr.length.
--> i - 1 where: i - 1 >= 0.
--> j where: arr[i] == arr[j] and i != j.

Return the minimum number of steps to reach the last index of the array.

Notice that you can not jump outside of the array at any time.

Link:
https://leetcode.com/problems/jump-game-iv/description/?envType=daily-question&envId=2026-05-18
*/
func minJumps(arr []int) int {
	// For every value, make sure we know the indices it corresponds to
	valToI := make(map[int]map[int]bool)
	for i := range arr {
		if _, ok := valToI[arr[i]]; !ok {
			valToI[arr[i]] = make(map[int]bool)
		}
		valToI[arr[i]][i] = true
	}

	// Now we breadth-first-search from the end position
	hops := 0
	visited := make([]bool, len(arr))
	idxQueue := datastructures.NewQueue[int]()
	visited[len(arr)-1] = true
	idxQueue.Enqueue(len(arr) - 1)
	for !idxQueue.Empty() {
		numToDequeue := idxQueue.Size()
		for range numToDequeue {
			next := idxQueue.Dequeue()
			if next == 0 {
				return hops
			} else {
				for n := range valToI[arr[next]] {
					if !visited[n] {
						visited[n] = true
						idxQueue.Enqueue(n)
					}
					delete(valToI[arr[next]], n)
				}
				// Sequential neighbors
				if next+1 < len(arr) && !visited[next+1] {
					visited[next+1] = true
					idxQueue.Enqueue(next + 1)
				}
				if !visited[next-1] {
					visited[next-1] = true
					idxQueue.Enqueue(next - 1)
				}
			}
		}
		hops++
	}

	// The code WILL never reach here
	return -1
}
