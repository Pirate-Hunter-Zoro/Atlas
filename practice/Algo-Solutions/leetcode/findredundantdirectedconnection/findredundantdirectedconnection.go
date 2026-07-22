package findredundantdirectedconnection

import "algo-solutions/datastructures"

/*
In this problem, a rooted tree is a directed graph such that, there is exactly one node (the root) for which all other nodes are descendants of this node, plus every node has exactly one parent, except for the root node which has no parents.

The given input is a directed graph that started as a rooted tree with n nodes (with distinct values from 1 to n), with one additional directed edge added.
The added edge has two different vertices chosen from 1 to n, and was not an edge that already existed.

The resulting graph is given as a 2D-array of edges.
Each element of edges is a pair [uᵢ, vᵢ] that represents a directed edge connecting nodes uᵢ and vᵢ, where uᵢ is a parent of child vᵢ.

Return an edge that can be removed so that the resulting graph is a rooted tree of n nodes.
If there are multiple answers, return the answer that occurs last in the given 2D-array.

Link:
https://leetcode.com/problems/redundant-connection-ii/description/
*/
func findRedundantDirectedConnection(edges [][]int) []int {
	// First iterate through our nodes and see if we have any node with two parents - if we do those are our two suspect edges
	parents := make([]int, len(edges)+1)
	// We know there is an extra edge - so the number of nodes is the number of edges since the edges in a tree is n-1 AND the nodes are 1-indexed so add an additional spot in the array for sanity
	for i := range parents {
		parents[i] = -1
	}
	suspect := []int{-1, -1, -1}
	for i := range edges {
		edge := edges[i]
		a := edge[0]
		b := edge[1]
		if parents[b] == -1 {
			parents[b] = a
		} else {
			// b now has two parents - store them both as our suspect
			suspect = []int{parents[b], a, b}
		}
	}

	// See if we create a cycle without the suspect edge
	nodeSet := datastructures.NewDisjointSet[int]()
	for i := range edges {
		edge := edges[i]
		a := edge[0]
		b := edge[1]
		nodeSet.Add(a)
		nodeSet.Add(b)
		if suspect[2] != b || suspect[1] != a {
			// (a,b) is the edge we are NOT including as we union, so if this is the case we are fine
			if nodeSet.Same(a, b) {
				// We have a cycle and we got this cycle WITHOUT including the second suspect edge - so we must remove the first suspect edge
				if suspect[0] != -1 {
					return []int{suspect[0], suspect[2]}
				} else {
					// No node had two parents, but this edge DOES create a cycle so it's the one to return
					return edge
				}
			} else {
				// Add both of these connected nodes to the same set and continue
				nodeSet.Join(a, b)
			}
		}
	}
	// If no cycle was seen without our second suspect edge, we gotta return that edge
	return []int{suspect[1], suspect[2]}
}
