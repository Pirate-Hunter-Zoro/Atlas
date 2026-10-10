package traprainwater

import "algo-solutions/datastructures"

/*
Given an m x n integer matrix heightMap representing the height of each unit cell in a 2D elevation map, return the volume of water it can trap after raining.

Link:
https://leetcode.com/problems/trapping-rain-water-ii/description/
*/
func trapRainWater(heightMap [][]int) int {
	type cell struct {
		row    int
		col    int
		height int
	}
	cellHeap := datastructures.NewHeap(func(first cell, second cell) bool {
		return first.height <= second.height
	})
	visited := make([][]bool, len(heightMap))
	for i := range visited {
		visited[i] = make([]bool, len(heightMap[i]))
	}

	// Add the border to the queue
	for i := range heightMap {
		cellHeap.Push(cell{
			i,
			0,
			heightMap[i][0],
		})
		visited[i][0] = true
		cellHeap.Push(cell{
			i,
			len(heightMap[i]) - 1,
			heightMap[i][len(heightMap[i])-1],
		})
		visited[i][len(heightMap[i])-1] = true
	}
	for j := range heightMap[0] {
		cellHeap.Push(cell{
			0,
			j,
			heightMap[0][j],
		})
		visited[0][j] = true
		cellHeap.Push(cell{
			len(heightMap) - 1,
			j,
			heightMap[len(heightMap)-1][j],
		})
		visited[len(heightMap)-1][j] = true
	}

	// Pull from the heap
	water := 0
	for !cellHeap.Empty() {
		// Grab cell info
		next := cellHeap.Pop()
		row := next.row
		col := next.col
		height := next.height
		// Look at unvisited neighbors
		unvisitedNeighbors := []cell{}
		if row > 0 {
			if !visited[row-1][col] {
				unvisitedNeighbors = append(unvisitedNeighbors, cell{
					row - 1,
					col,
					heightMap[row-1][col],
				})
			}
		}
		if col > 0 {
			if !visited[row][col-1] {
				unvisitedNeighbors = append(unvisitedNeighbors, cell{
					row,
					col - 1,
					heightMap[row][col-1],
				})
			}
		}
		if row < len(heightMap)-1 {
			if !visited[row+1][col] {
				unvisitedNeighbors = append(unvisitedNeighbors, cell{
					row + 1,
					col,
					heightMap[row+1][col],
				})
			}
		}
		if col < len(heightMap[row])-1 {
			if !visited[row][col+1] {
				unvisitedNeighbors = append(unvisitedNeighbors, cell{
					row,
					col + 1,
					heightMap[row][col+1],
				})
			}
		}
		// Look at the invisited neighbors
		for _, neighbor := range unvisitedNeighbors {
			visited[neighbor.row][neighbor.col] = true
			if neighbor.height < height {
				// Found a pit to fill with water
				water += height - neighbor.height
				neighbor.height = height // New effective height of neighbor now that it is filled with water
			}
			cellHeap.Push(neighbor)
		}
	}
	return water
}
