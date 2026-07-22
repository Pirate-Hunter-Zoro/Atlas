package findredundantconnection

import "algo-solutions/datastructures"

/*
In this problem, a tree is an undirected graph that is connected and has no cycles.

You are given a graph that started as a tree with n nodes labeled from 1 to n, with one additional edge added.
The added edge has two different vertices chosen from 1 to n, and was not an edge that already existed.
The graph is represented as an array edges of length n where edges[i] = [aᵢ, bᵢ] indicates that there is an edge between nodes aᵢ and bᵢ in the graph.

Return an edge that can be removed so that the resulting graph is a tree of n nodes.
If there are multiple answers, return the answer that occurs last in the input.

Link:
https://leetcode.com/problems/redundant-connection/description/?envType=problem-list-v2&envId=union-find
*/
func findRedundantConnection(edges [][]int) []int {
	nodeSet := datastructures.NewDisjointSet[int]()
	for i := range edges {
		edge := edges[i]
		nodeSet.Add(edge[0])
		nodeSet.Add(edge[1])
		if nodeSet.Same(edge[0], edge[1]) {
			// Created a cycle
			return edge
		} else {
			// The two nodes are part of the same path now
			nodeSet.Join(edge[0], edge[1])
		}
	}
	return nil
}
