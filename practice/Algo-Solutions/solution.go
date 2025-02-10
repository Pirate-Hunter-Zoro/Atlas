package leetcode

import (
	"leet-code/datastructures"
	"leet-code/helpermath"
	"math"
)

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given n identical eggs and you have access to a building with k floors labeled from 1 to n.

You know that there exists a floor f where 0 <= f <= n such that any egg dropped at a floor higher than f will break, and any egg dropped at or below floor f will not break.

Each move, you may take an unbroken egg and drop it from any floor x (where 1 <= x <= n).
If the egg breaks, you can no longer use it.
However, if the egg does not break, you may reuse it in future moves.

Return the minimum number of moves that you need to determine with certainty what the value of f is.

Inpsiration:
https://brilliant.org/wiki/egg-dropping/
*/
func superEggDrop(n int, k int) int {
    // We need to be able to cover n floors...
	// How many drops will it take to cover k floors with n eggs? Binary search...
	left := 1
	right := k
	chooser := helpermath.NewChooseCalculator()
	for left < right {
		mid := int((left + right) / 2)
		num_floors_covered := 0
		// Calculate the number of floors covered given that we have 'mid' drops and n eggs
		for i:=1; i<=n; i++ {
			// From the article
			num_floors_covered += chooser.Choose(mid, i)
			if num_floors_covered < 0 { // avoid integer overflow
				num_floors_covered = int(math.MaxInt)
				break
			}
		}
		if num_floors_covered < k {
			// Need more drops
			left = mid + 1
		} else if num_floors_covered > k {
			// Try using less drops
			right = mid
		} else {
			return mid
		}
	}

	return left
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an array of integers heights representing the histogram's bar height where the width of each bar is 1, return the area of the largest rectangle in the histogram.
*/
func largestRectangleArea(heights []int) int {
	// Answer the question - at this index, what's the farthest right I can go before I run into someone shorter
	shorter_right := make([]int, len(heights))
	for i:=0; i<len(shorter_right); i++ {
		shorter_right[i] = len(heights)
	}
	right_stack := datastructures.NewStack[int]()
	right_stack.Push(0)
	for i, h := range heights {
		if i == 0 {
			continue
		} else {
			for !right_stack.Empty() && heights[right_stack.Peek()] > h {
				shorter_right[right_stack.Pop()] = i
			}
			right_stack.Push(i)
		}
	}
	// Now same for left
	shorter_left := make([]int, len(heights))
	for i:=0; i<len(shorter_left); i++ {
		shorter_left[i] = -1
	}
	left_stack := datastructures.NewStack[int]()
	left_stack.Push(len(heights)-1)
	for i:=len(heights)-2; i>=0; i-- {
		h := heights[i]
		for !left_stack.Empty() && heights[left_stack.Peek()] > h {
			shorter_left[left_stack.Pop()] = i
		}
		left_stack.Push(i)
	}

	record := 0
	for i, h := range heights {
		record = max(record, h * (shorter_right[i]-shorter_left[i]-1))
	}
	return record
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given a rows x cols binary matrix filled with 0's and 1's, find the largest rectangle containing only 1's and return its area.
*/
func maximalRectangle(matrix [][]byte) int {
	// Keep a running histogram going
	heights := make([]int, len(matrix[0]))
	record := 0
	for _, row := range matrix {
		for i, c := range row {
			if c == '1' {
				heights[i] += 1
			} else {
				heights[i] = 0
			}
		}
		record = max(record, largestRectangleArea(heights))
	}

    return record
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There is a 50 x 50 chessboard with one knight and some pawns on it. 
You are given two integers kx and ky where (kx, ky) denotes the position of the knight, and a 2D array positions where positions[i] = [xi, yi] denotes the position of the pawns on the chessboard.

Alice and Bob play a turn-based game, where Alice goes first. 
In each player's turn:
- The player selects a pawn that still exists on the board and captures it with the knight in the fewest possible moves. 
  Note that the player can select any pawn, it might not be one that can be captured in the least number of moves.
- In the process of capturing the selected pawn, the knight may pass other pawns without capturing them. 
  Only the selected pawn can be captured in this turn.
- Alice is trying to maximize the sum of the number of moves made by both players until there are no more pawns on the board, whereas Bob tries to minimize them.

Return the maximum total number of moves made during the game that Alice can achieve, assuming both players play optimally.

Note that in one move, a chess knight has eight possible positions it can move to, as illustrated below. 
Each move is two cells in a cardinal direction, then one cell in an orthogonal direction.
*/
func maxMoves(kx int, ky int, positions [][]int) int {
	board_size := 50

	// We need to store the solutions for the minimum number of moves to reach any position from any other
	min_hops_to_reach := make([][][][]int, board_size)
	for i:=0; i<board_size; i++ {
		min_hops_to_reach[i] = make([][][]int, board_size)
		for j:=0; j<board_size; j++ {
			min_hops_to_reach[i][j] = make([][]int, board_size)
			for k:=0; k<board_size; k++ {
				min_hops_to_reach[i][j][k] = make([]int, board_size)
			}
		}
	}

	// Using bit-masking, we will remember the solutions for the minimizer and maximizer given the remaining positions
	maximizer_sols := make([][]map[int]int, board_size)
	minimizer_sols := make([][]map[int]int, board_size)
	for i:=0; i<board_size; i++ {
		maximizer_sols[i] = make([]map[int]int, board_size)
		minimizer_sols[i] = make([]map[int]int, board_size)
		for j:=0; j<board_size; j++ {
			maximizer_sols[i][j] = make(map[int]int)
			minimizer_sols[i][j] = make(map[int]int)
		}
	}

	initial_bit_mask := int(math.Pow(2, float64(len(positions)-1))) - 1
	return maximizer(kx, ky, initial_bit_mask, maximizer_sols, minimizer_sols, positions, min_hops_to_reach)
}

// Helper function to maximize the number of moves to take all the remaining pawns
func maximizer(x int, y int, positions_bit_mask int, maximizer_sols [][]map[int]int, minimizer_sols [][]map[int]int, positions [][]int, min_hops_to_reach [][][][]int) int {
	_, ok := maximizer_sols[x][y][positions_bit_mask]
	if !ok {
		remaining_positions := [][]int{}
		for i:=0; i<len(positions); i++ {
			if (1 << i & positions_bit_mask) > 0 {
				remaining_positions = append(remaining_positions, positions[i])
			}
		}
		if len(remaining_positions) == 1 {
			// No choice but to take the remaining pawn
			pawn_x, pawn_y := remaining_positions[0][0], remaining_positions[0][1]
			maximizer_sols[x][y][positions_bit_mask] = movesToTake(x, y, pawn_x, pawn_y, min_hops_to_reach)
		} else {
			// Try taking every possible first pawn and see what that leaves the minimizer with
			record := int(math.MinInt)
			for idx, posn := range(remaining_positions) {
				pawn_x, pawn_y := posn[0], posn[1]
				new_bit_mask := (1 << idx) ^ positions_bit_mask
				record = max(record, movesToTake(x, y, pawn_x, pawn_y, min_hops_to_reach) + minimizer(pawn_x, pawn_y, new_bit_mask, maximizer_sols, minimizer_sols, positions, min_hops_to_reach))
			}
			maximizer_sols[x][y][positions_bit_mask] = record
		}
	}
	return maximizer_sols[x][y][positions_bit_mask]
}

// Helper function to maximize the number of moves to take all the remaining pawns
func minimizer(x int, y int, positions_bit_mask int, maximizer_sols [][]map[int]int, minimizer_sols [][]map[int]int, positions [][]int, min_hops_to_reach [][][][]int) int {
	_, ok := minimizer_sols[x][y][positions_bit_mask]
	if !ok {
		remaining_positions := [][]int{}
		for i:=0; i<len(positions); i++ {
			if (1 << i & positions_bit_mask) > 0 {
				remaining_positions = append(remaining_positions, positions[i])
			}
		}
		if len(remaining_positions) == 1 {
			// No choice but to take the remaining pawn
			pawn_x, pawn_y := remaining_positions[0][0], remaining_positions[0][1]
			minimizer_sols[x][y][positions_bit_mask] = movesToTake(x, y, pawn_x, pawn_y, min_hops_to_reach)
		} else {
			// Try taking every possible first pawn and see what that leaves the minimizer with
			record := int(math.MaxInt)
			for idx, posn := range(remaining_positions) {
				pawn_x, pawn_y := posn[0], posn[1]
				new_bit_mask := (1 << idx) ^ positions_bit_mask
				record = min(record, movesToTake(x, y, pawn_x, pawn_y, min_hops_to_reach) + maximizer(pawn_x, pawn_y, new_bit_mask, maximizer_sols, minimizer_sols, positions, min_hops_to_reach))
			}
			minimizer_sols[x][y][positions_bit_mask] = record
		}
	}
	return minimizer_sols[x][y][positions_bit_mask]
}

// Helper function to determine the number of moves necessary to take a pawn at a given position
func movesToTake(knight_x int, knight_y int, pawn_x int, pawn_y int, min_hops_to_reach [][][][]int) int {
	if knight_x == pawn_x && knight_y == pawn_y {
		return 0
	} else if min_hops_to_reach[knight_x][knight_y][pawn_x][pawn_y] == 0 && min_hops_to_reach[pawn_x][pawn_y][knight_x][knight_y] == 0 {
		// Need to solve this problem - use BFS
		// Try all (up to 8) possible moves by the knight and see which one yields the best solution
		bfs_queue := datastructures.NewQueue[[]int]()
		bfs_queue.Enqueue([]int{knight_x,knight_y})
		visited := make([][]bool, len(min_hops_to_reach))
		for i:=0; i<len(min_hops_to_reach); i++ {
			visited[i] = make([]bool, len(min_hops_to_reach))
		}
		hops := 0
		found := false
		for !bfs_queue.Empty() {
			for i:=0; i<bfs_queue.Size(); i++ {
				next := bfs_queue.Dequeue()
				knight_x, knight_y = next[0], next[1]
				if knight_x == pawn_x && knight_y == pawn_y {
					found = true
					break
				}
				if !visited[knight_x][knight_y] {
					visited[knight_x][knight_y] = true
					if knight_x > 0 && knight_y > 1{
						// Try up two, left one
						new_knight_x := knight_x-1
						new_knight_y := knight_y-2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < len(min_hops_to_reach)-1 && knight_y > 1{
						// Try up two, right one
						new_knight_x := knight_x+1
						new_knight_y := knight_y-2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x > 1 && knight_y > 0{
						// Try up one, left two
						new_knight_x := knight_x-2
						new_knight_y := knight_y-1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < len(min_hops_to_reach)-2 && knight_y > 1 {
						// Try up one, right two
						new_knight_x := knight_x+2
						new_knight_y := knight_y-1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x > 0 && knight_y < len(min_hops_to_reach)-2 {
						// Try down two, left one
						new_knight_x := knight_x-1
						new_knight_y := knight_y+2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < len(min_hops_to_reach)-2 && knight_y < len(min_hops_to_reach)-2{
						// Try down two, right one
						new_knight_x := knight_x+1
						new_knight_y := knight_y+2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x > 1 && knight_y < len(min_hops_to_reach)-1 {
						// Try down one, left two
						new_knight_x := knight_x-2
						new_knight_y := knight_y+1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < len(min_hops_to_reach)-1 && knight_y < len(min_hops_to_reach)-1 {
						// Try down one, right two
						new_knight_x := knight_x+2
						new_knight_y := knight_y+1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
				}
			}
			if found {
				break
			}
			hops++
		}
		min_hops_to_reach[knight_x][knight_y][pawn_x][pawn_y] = hops
	} else {
		sol := max(min_hops_to_reach[knight_x][knight_y][pawn_x][pawn_y], min_hops_to_reach[pawn_x][pawn_y][knight_x][knight_y])
		min_hops_to_reach[knight_x][knight_y][pawn_x][pawn_y] = sol
		min_hops_to_reach[pawn_x][pawn_y][knight_x][knight_y] = sol
	}
	return min_hops_to_reach[knight_x][knight_y][pawn_x][pawn_y]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

