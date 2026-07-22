package mintimetoreachii

import (
	"algo-solutions/datastructures"
	"math"
)

/*
There is a dungeon with n x m rooms arranged as a grid.

You are given a 2D array moveTime of size n x m, where moveTime[i][j] represents the minimum time in seconds when you can start moving to that room.
You start from the room (0, 0) at time t = 0 and can move to an adjacent room.
Moving between adjacent rooms takes one second for one move and two seconds for the next, alternating between the two.

Return the minimum time to reach the room (n - 1, m - 1).

Two rooms are adjacent if they share a common wall, either horizontally or vertically.

Link:
https://leetcode.com/problems/find-minimum-time-to-reach-last-room-ii/description/
*/
func minTimeToReachII(moveTime [][]int) int {
	// This is a AGAIN shortest path problem
	type connection struct {
		row          int
		col          int
		cost         int
		lastJumpTime int // either 1 or 2
	}
	connectionHeap := datastructures.NewHeap(func(c1, c2 *connection) bool {
		return c1.cost < c2.cost
	})
	connectionHeap.Push(&connection{row: 0, col: 0, cost: 0, lastJumpTime: 2})
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
		nextJumpTime := 1
		if node.lastJumpTime == 1 {
			// Then this jump time is 2
			nextJumpTime++
		}
		if node.row > 0 {
			// Up
			newCost := max(node.cost, moveTime[node.row-1][node.col]) + nextJumpTime
			if newCost < minCost[node.row-1][node.col] {
				// Worth exploring
				minCost[node.row-1][node.col] = newCost
				connectionHeap.Push(&connection{row: node.row - 1, col: node.col, cost: newCost, lastJumpTime: nextJumpTime})
			}
		}
		if node.row < len(moveTime)-1 {
			// Down
			newCost := max(node.cost, moveTime[node.row+1][node.col]) + nextJumpTime
			if newCost < minCost[node.row+1][node.col] {
				minCost[node.row+1][node.col] = newCost
				connectionHeap.Push(&connection{row: node.row + 1, col: node.col, cost: newCost, lastJumpTime: nextJumpTime})
			}
		}
		if node.col > 0 {
			// Left
			newCost := max(node.cost, moveTime[node.row][node.col-1]) + nextJumpTime
			if newCost < minCost[node.row][node.col-1] {
				minCost[node.row][node.col-1] = newCost
				connectionHeap.Push(&connection{row: node.row, col: node.col - 1, cost: newCost, lastJumpTime: nextJumpTime})
			}
		}
		if node.col < len(moveTime[0])-1 {
			// Right
			newCost := max(node.cost, moveTime[node.row][node.col+1]) + nextJumpTime
			if newCost < minCost[node.row][node.col+1] {
				minCost[node.row][node.col+1] = newCost
				connectionHeap.Push(&connection{row: node.row, col: node.col + 1, cost: newCost, lastJumpTime: nextJumpTime})
			}
		}
	}
	return minCost[len(moveTime)-1][len(moveTime[0])-1]
}
