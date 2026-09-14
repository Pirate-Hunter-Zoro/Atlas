package mintimetoreach

import (
	"algo-solutions/datastructures"
	"math"
)

/*
There is a dungeon with n x m rooms arranged as a grid.

You are given a 2D array moveTime of size n x m, where moveTime[i][j] represents the minimum time in seconds when you can start moving to that room.
You start from the room (0, 0) at time t = 0 and can move to an adjacent room.
Moving between adjacent rooms takes exactly one second.

Return the minimum time to reach the room (n - 1, m - 1).

Two rooms are adjacent if they share a common wall, either horizontally or vertically.

Link:
https://leetcode.com/problems/find-minimum-time-to-reach-last-room-i/description/?envType=daily-question&envId=2025-05-07
*/
func minTimeToReach(moveTime [][]int) int {
	// This is a shortest path problem
	type connection struct {
		row  int
		col  int
		cost int
	}
	connectionHeap := datastructures.NewHeap(func(c1, c2 *connection) bool {
		return c1.cost < c2.cost
	})
	connectionHeap.Push(&connection{row: 0, col: 0, cost: 0})
	minCost := make([][]int, len(moveTime))
	for i := range moveTime {
		minCost[i] = make([]int, len(moveTime[0]))
		for j := range moveTime[0] {
			minCost[i][j] = math.MaxInt
		}
	}
	minCost[0][0] = 0
	for !connectionHeap.Empty() {
		node := connectionHeap.Pop()
		if node.row == len(moveTime)-1 && node.col == len(moveTime[0])-1 {
			break
		}
		// Look up, down, left, right
		if node.row > 0 {
			// Up
			newCost := max(node.cost, moveTime[node.row-1][node.col]) + 1
			if newCost < minCost[node.row-1][node.col] {
				// Worth exploring
				minCost[node.row-1][node.col] = newCost
				connectionHeap.Push(&connection{row: node.row - 1, col: node.col, cost: max(node.cost, moveTime[node.row-1][node.col]) + 1})
			}
		}
		if node.row < len(moveTime)-1 {
			// Down
			newCost := max(node.cost, moveTime[node.row+1][node.col]) + 1
			if newCost < minCost[node.row+1][node.col] {
				minCost[node.row+1][node.col] = newCost
				connectionHeap.Push(&connection{row: node.row + 1, col: node.col, cost: max(node.cost, moveTime[node.row+1][node.col]) + 1})
			}
		}
		if node.col > 0 {
			// Left
			newCost := max(node.cost, moveTime[node.row][node.col-1]) + 1
			if newCost < minCost[node.row][node.col-1] {
				minCost[node.row][node.col-1] = newCost
				connectionHeap.Push(&connection{row: node.row, col: node.col - 1, cost: max(node.cost, moveTime[node.row][node.col-1]) + 1})
			}
		}
		if node.col < len(moveTime[0])-1 {
			// Right
			newCost := max(node.cost, moveTime[node.row][node.col+1]) + 1
			if newCost < minCost[node.row][node.col+1] {
				minCost[node.row][node.col+1] = newCost
				connectionHeap.Push(&connection{row: node.row, col: node.col + 1, cost: max(node.cost, moveTime[node.row][node.col+1]) + 1})
			}
		}
	}
	return minCost[len(moveTime)-1][len(moveTime[0])-1]
}
