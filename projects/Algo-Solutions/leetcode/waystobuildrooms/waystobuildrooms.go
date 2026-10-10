package waystobuildrooms

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
You are an ant tasked with adding n new rooms numbered 0 to n-1 to your colony.
You are given the expansion plan as a 0-indexed integer array of length n, prevRoom, where prevRoom[i] indicates that you must build room prevRoom[i] before building room i, and these two rooms must be connected directly.
Room 0 is already built, so prevRoom[0] = -1.
The expansion plan is given such that once all the rooms are built, every room will be reachable from room 0.

You can only build one room at a time, and you can travel freely between rooms you have already built only if they are connected.
You can choose to build any room as long as its previous room is already built.

Return the number of different orders you can build all the rooms in.
Since the answer may be large, return it modulo 10⁹ + 7.

Link:
https://leetcode.com/problems/count-ways-to-build-rooms-in-an-ant-colony/description/?envType=problem-list-v2&envId=topological-sort
*/
func waysToBuildRooms(prevRoom []int) int {
	// First create our underlying graph structure
	graph := make([][]int, len(prevRoom))
	for i := range prevRoom {
		graph[i] = make([]int, 0) // Initialize each room's adjacency list
	}
	for i := 1; i < len(prevRoom); i++ {
		graph[prevRoom[i]] = append(graph[prevRoom[i]], i) // Add the current room to the graph as a child of the previous room
	}
	sols := make([]int, len(prevRoom))
	subtreeCounts := make([]int, len(prevRoom))
	for i := range prevRoom {
		sols[i] = -1
	}
	calculator := helpermath.NewChooseCalculator()
	return topDownCountBuildRooms(0, sols, subtreeCounts, graph, calculator)
}

/*
Starting at the given tree root, count the number of ways to build all such rooms in this subtree ant colony
*/
func topDownCountBuildRooms(room int, sols []int, subtreeCounts []int, graph [][]int, calculator *helpermath.ChooseCalculator) int {
	if sols[room] == -1 {
		// We need to solve this problem
		waysToBuild := []int{}
		subtreeCounts[room] = 1
		for _, subtree := range graph[room] {
			waysToBuild = append(waysToBuild, topDownCountBuildRooms(subtree, sols, subtreeCounts, graph, calculator))
			subtreeCounts[room] += subtreeCounts[subtree]
		}
		totalWays := 1
		// All of the subtrees have their individual ways of being ordered, and we can intersperse the subtrees in any which way
		// First, suppose we select a SET ordering for each subtree - count the ways to intersperse
		total := subtreeCounts[room] - 1 // Don't include the parent
		for _, subtree := range graph[room] {
			totalWays = helpermath.ModMul(totalWays, calculator.ChooseMod(total, subtreeCounts[subtree], leetcode.MOD), leetcode.MOD)
			total -= subtreeCounts[subtree]
		}
		// Now that we've counted all the ways to intersperse one particular ording assignment for all subtrees, multiply by the total number of ording assignments across all subtrees
		for _, numWaysForSubtree := range waysToBuild {
			totalWays = helpermath.ModMul(totalWays, numWaysForSubtree, leetcode.MOD)
		}
		sols[room] = totalWays
	}

	return sols[room]
}
