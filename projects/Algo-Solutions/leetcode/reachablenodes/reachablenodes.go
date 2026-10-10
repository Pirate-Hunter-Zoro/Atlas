package reachablenodes

import "algo-solutions/datastructures"

/*
You are given an undirected graph (the "original graph") with n nodes labeled from 0 to n - 1.
You decide to subdivide each edge in the graph into a chain of nodes, with the number of new nodes varying between each edge.

The graph is given as a 2D array of edges where edges[i] = [uᵢ, vᵢ, cntᵢ] indicates that there is an edge between nodes ui and vi in the original graph, and cntᵢ is the total number of new nodes that you will subdivide the edge into. Note that cntᵢ == 0 means you will not subdivide the edge.

To subdivide the edge [uᵢ, vᵢ], replace it with (cntᵢ + 1) new edges and cntᵢ new nodes. The new nodes are x1, x2, ..., xcntᵢ, and the new edges are [uᵢ, x1], [x1, x2], [x2, x3], ..., [xcnt{i-1}, xcntᵢ], [xcntᵢ, vᵢ].

In this new graph, you want to know how many nodes are reachable from the node 0, where a node is reachable if the distance is maxMoves or less.

Given the original graph and maxMoves, return the number of nodes that are reachable from node 0 in the new graph.

Link:
https://leetcode.com/problems/reachable-nodes-in-subdivided-graph/description/?envType=problem-list-v2&envId=shortest-path
*/
func reachableNodes(edges [][]int, maxMoves int, n int) int {
	// Construct graph and keep track of the splits of each edge
	graph := make([][][]int, n)
	// Due to the nuance of this problem, for each edge we'll need to keep track which way we've traversed it
	traversed := make([][]int, n)
	for i := range n {
		traversed[i] = make([]int, n)
	}
	for i := range len(edges) {
		u := edges[i][0]
		v := edges[i][1]
		cuts := edges[i][2]
		graph[u] = append(graph[u], []int{v, cuts + 1}) // True edge cost
		graph[v] = append(graph[v], []int{u, cuts + 1})
	}

	// Before we consider divisions, we need to first find out how many hops it takes to reach each node from node zero
	nodeHeap := datastructures.NewHeap(func(nodeA []int, nodeB []int) bool {
		return nodeA[1] < nodeB[1]
	})
	nodeHeap.Push([]int{0, 0})
	reachable := 0
	visited := make([]bool, n)
	// Find the shortest path from node zero to all other nodes, and any that are within the distance (careful counting with the newly split edges) not already reached contribute to the count
	for !nodeHeap.Empty() {
		nextNode := nodeHeap.Pop()
		node := nextNode[0]
		cost := nextNode[1]
		if cost <= maxMoves && !visited[node] {
			reachable++
			visited[node] = true
			// Now enqueue the neighbors of this node
			for _, edge := range graph[node] {
				neighbor := edge[0]
				edgeCost := edge[1]
				newCost := cost + edgeCost
				// That edge was actually a bunch of neighbors in between due to the splits
				reachable += edgeCost - 1 - max(0, newCost-maxMoves-1) // Not allowed to move to any intermediate nodes that exceeded the moves allowed
				nodeHeap.Push([]int{neighbor, newCost})
				traversed[node][neighbor] = edgeCost - 1 - max(0, newCost-maxMoves-1) // Keep track of how many nodes we counted going along the connection in this direction
				// HOWEVER, that may have double counted some nodes in between if we have traversed this connection from the other direction before
				reachable -= max(0, traversed[node][neighbor]+traversed[neighbor][node]-(edgeCost-1)) // edgeCost - 1 is the total number of nodes in between node and neighbor, so this covers overcounting
			}
		}
	}

	return reachable
}
