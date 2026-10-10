package mincost

import (
	"algo-solutions/datastructures"
	"math"
)

/*
There is a country of n cities numbered from 0 to n - 1 where all the cities are connected by bi-directional roads.
The roads are represented as a 2D integer array edges where edges[i] = [xᵢ, yᵢ, timeᵢ] denotes a road between cities xᵢ and yᵢ that takes timei minutes to travel.
There may be multiple roads of differing travel times connecting the same two cities, but no road connects a city to itself.

Each time you pass through a city, you must pay a passing fee.
This is represented as a 0-indexed integer array passingFees of length n where passingFees[j] is the amount of dollars you must pay when you pass through city j.

In the beginning, you are at city 0 and want to reach city n - 1 in maxTime minutes or less.
The cost of your journey is the summation of passing fees for each city that you passed through at some moment of your journey (including the source and destination cities).

Given maxTime, edges, and passingFees, return the minimum cost to complete your journey, or -1 if you cannot complete it within maxTime minutes.

Link:
https://leetcode.com/problems/minimum-cost-to-reach-destination-in-time/description/
*/
func minCost(maxTime int, edges [][]int, passingFees []int) int {
	// This will be a modified Djikstra's algorithm that will keep finding shorter and shorter paths until one is cheap enough
	type heapInput struct {
		node int
		cost int
		time int
	}

	// Find n
	n := len(passingFees)

	// First create our connectivity list graph
	graph := make([][][]int, n)
	for i := range graph {
		graph[i] = make([][]int, 0)
	}
	for edgeIdx := range edges {
		edge := edges[edgeIdx]
		// Store each bidirectional connection and its time
		graph[edge[0]] = append(graph[edge[0]], []int{edge[1], edge[2]})
		graph[edge[1]] = append(graph[edge[1]], []int{edge[0], edge[2]})
	}

	// Now prepare our heap for Djikstra
	nodeHeap := datastructures.NewHeap(func(first, second *heapInput) bool {
		return first.cost < second.cost
	})
	nodeHeap.Push(&heapInput{
		node: 0,
		cost: passingFees[0],
		time: 0,
	})

	// Note that our implementation of Djikstra's algorithm will guarantee that when we reach a node, we've already done it with the minimum cost
	// Keeping track of the minimum time to reach a node ensures that we will NEVER add a node if doing so only reaches it in both a slower time AND more cost
	minTime := make([]int, n)
	for i := range n {
		minTime[i] = math.MaxInt64
	}

	// Now we begin
	for !nodeHeap.Empty() {
		nextNode := nodeHeap.Pop()
		currId := nextNode.node
		currCost := nextNode.cost
		currTime := nextNode.time
		if currId == n-1 && currTime <= maxTime {
			return currCost
		}
		for connectionIdx := range graph[currId] {
			dest := graph[currId][connectionIdx]
			nextId := dest[0]
			nextCost := currCost + passingFees[nextId]
			nextTime := currTime + dest[1]
			if minTime[nextId] > nextTime && nextTime <= maxTime {
				// This is worth exploring, because even if we've already seen this node before for a cheaper cost, now we're doing it in less time
				minTime[nextId] = nextTime
				nodeHeap.Push(&heapInput{
					node: nextId,
					cost: nextCost,
					time: nextTime,
				})
			}
		}
	}

	return -1
}
