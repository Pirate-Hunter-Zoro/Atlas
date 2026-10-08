package minimumcost

import (
	"algo-solutions/datastructures"
	"math"
)

/*
You are given two 0-indexed strings source and target, both of length n and consisting of lowercase English characters.
You are also given two 0-indexed string arrays original and changed, and an integer array cost, where cost[i] represents the cost of converting the string original[i] to the string changed[i].

You start with the string source.
In one operation, you can pick a substring x from the string, and change it to y at a cost of z if there exists any index j such that cost[j] == z, original[j] == x, and changed[j] == y.
You are allowed to do any number of operations, but any pair of operations must satisfy either of these two conditions:
- The substrings picked in the operations are source[a..b] and source[c..d] with either b < c or d < a. In other words, the indices picked in both operations are disjoint.
- The substrings picked in the operations are source[a..b] and source[c..d] with a == c and b == d. In other words, the indices picked in both operations are identical.

Return the minimum cost to convert the string source to the string target using any number of operations.
If it is impossible to convert source to target, return -1.

Note that there may exist indices i, j such that original[j] == original[i] and changed[j] == changed[i].

Link:
https://leetcode.com/problems/minimum-cost-to-convert-string-ii/description/?envType=daily-question&envId=2026-01-30
*/
func minimumCost(source string, target string, original []string, changed []string, cost []int) int64 {
	// Map each string in the original and changed strings to an id
	stringToId := make(map[string]int)
	count := 0
	for i := range original {
		if _, ok := stringToId[original[i]]; !ok {
			stringToId[original[i]] = count
			count += 1
		}
		if _, ok := stringToId[changed[i]]; !ok {
			stringToId[changed[i]] = count
			count += 1
		}
	}

	// For each string from original and changed, find the shortest distance
	distances := make([][]int64, count)
	for i := range distances {
		distances[i] = make([]int64, count)
		for j := range distances[i] {
			distances[i][j] = math.MaxInt / 2
		}
		distances[i][i] = 0
	}
	// Create graph
	for k := range original {
		firstId := stringToId[original[k]]
		secondId := stringToId[changed[k]]
		oldCost := distances[firstId][secondId]
		if int64(cost[k]) < oldCost {
			// Update cost if this is a better way to get from original[k] to changed[k]
			distances[firstId][secondId] = int64(cost[k])
		}
	}
	// Now use Floyd-Warshall algorithm
	for j := range distances { // Intermediate node
		for i := range distances { // Start node
			for k := range distances { // End node
				distances[i][k] = min(distances[i][k], distances[i][j]+distances[j][k])
			}
		}
	}

	// Given the shortest path from each original to each changed, perform string dynamic programming
	dp := make([]int64, len(source)+1) // dp[i] = min cost to convert source[i:] to target[i:]
	for i := range dp {
		dp[i] = math.MaxInt / 2
		if i == len(source) {
			dp[i] = 0 // Base case - empty string to empty string costs nothing
		}
	}
	var solve func(i int) int64
	trie := datastructures.NewTrie()
	for i, ogStr := range original {
		trie.Insert(ogStr, stringToId[ogStr])
		trie.Insert(changed[i], stringToId[changed[i]])
	}
	solve = func(i int) int64 {
		if dp[i] == math.MaxInt/2 {
			// Need to solve this problem
			if source[i] == target[i] {
				// Current character matches so go to subproblem
				candidate := solve(i + 1) // Candidate value
				if candidate != -1 {
					// Potential
					dp[i] = candidate
				}
			}
			// Iterate through all characters
			sourceCurr := trie
			changedCurr := trie
			for j := i; j < len(source); j++ {
				sourceCurr = trie.SearchNode(rune(source[j]), sourceCurr)
				changedCurr = trie.SearchNode(rune(target[j]), changedCurr)
				if trie.IsWord(sourceCurr) && trie.IsWord(changedCurr) {
					// Try swapping and then converting the rest
					rest := solve(j + 1)
					if rest != -1 {
						if dp[i] == -1 {
							dp[i] = distances[sourceCurr.GetId()][changedCurr.GetId()] + rest
						} else {
							dp[i] = min(dp[i], distances[sourceCurr.GetId()][changedCurr.GetId()]+rest)
						}
					}
				} else if sourceCurr == nil || changedCurr == nil {
					// Word mismatch so we must not allow continuing
					break
				}
			}

			// Impossible
			if dp[i] >= math.MaxInt/2 {
				dp[i] = -1
			}
		}
		return dp[i]
	}

	return solve(0)
}
