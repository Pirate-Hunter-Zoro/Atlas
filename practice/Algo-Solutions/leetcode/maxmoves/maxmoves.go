package maxmoves

import (
	"algo-solutions/datastructures"
	"math"
)

/*
There is a 50 x 50 chessboard with one knight and some pawns on it.
You are given two integers kx and ky where (kx, ky) denotes the position of the knight, and a 2D array positions where positions[i] = [xᵢ, yᵢ] denotes the position of the pawns on the chessboard.

Alice and Bob play a turn-based game, where Alice goes first.
In each player's turn:
  - The player selects a pawn that still exists on the board and captures it with the knight in the fewest possible moves.
    Note that the player can select any pawn, it might not be one that can be captured in the least number of moves.
  - In the process of capturing the selected pawn, the knight may pass other pawns without capturing them.
    Only the selected pawn can be captured in this turn.
  - Alice is trying to maximize the sum of the number of moves made by both players until there are no more pawns on the board, whereas Bob tries to minimize them.

Return the maximum total number of moves made during the game that Alice can achieve, assuming both players play optimally.

Note that in one move, a chess knight has eight possible positions it can move to, as illustrated below. Each move is two cells in a cardinal direction, then one cell in an orthogonal direction.

Link:
https://leetcode.com/problems/maximum-number-of-moves-to-kill-all-pawns/description/?envType=problem-list-v2&envId=game-theory
*/
func maxMoves(kx int, ky int, positions [][]int) int {
	// Map the initial knight position and all pawn positions to indices, and vice versa
	boardPosns := make([]int, 1+len(positions))
	boardPosns[0] = 50*kx + ky
	posnToIdx := make(map[int]int)
	posnToIdx[boardPosns[0]] = 0
	for i, posn := range positions {
		boardPosns[i+1] = 50*posn[0] + posn[1]
		posnToIdx[boardPosns[i+1]] = i + 1
	}

	dp := make([][]int, len(boardPosns))
	for i := range dp {
		dp[i] = make([]int, len(boardPosns))
		for j := range dp[i] {
			dp[i][j] = -1
		}
	}
	type posn struct {
		row int
		col int
	}
	var dist func(knightPosnIdx int, pawnPosnIdx int) int
	dist = func(knightPosnIdx int, pawnPosnIdx int) int {
		// BFS and store both ways
		if dp[knightPosnIdx][pawnPosnIdx] == -1 {
			// Need to solve this problem
			visited := make([]bool, 50*50)
			bfs := datastructures.NewQueue[int]()
			bfs.Enqueue(boardPosns[knightPosnIdx])
			hops := 0
			for !bfs.Empty() {
				n := bfs.Size()
				for range n {
					next := bfs.Dequeue()
					nextIdx, ok := posnToIdx[next]
					if ok {
						dp[knightPosnIdx][nextIdx] = hops
						dp[nextIdx][knightPosnIdx] = hops
					}
					// Enqueue unseen neighbors
					row := int(next / 50)
					col := next % 50
					// (Up to) eight neighbors
					farLeftUp := &posn{
						row - 1,
						col - 2,
					}
					farUpLeft := &posn{
						row - 2,
						col - 1,
					}
					farRightUp := &posn{
						row - 1,
						col + 2,
					}
					farUpRight := &posn{
						row - 2,
						col + 1,
					}
					farLeftDown := &posn{
						row + 1,
						col - 2,
					}
					farDownLeft := &posn{
						row + 2,
						col - 1,
					}
					farRightDown := &posn{
						row + 1,
						col + 2,
					}
					farDownRight := &posn{
						row + 2,
						col + 1,
					}
					neighbors := []*posn{
						farLeftUp,
						farUpLeft,
						farRightUp,
						farUpRight,
						farLeftDown,
						farDownLeft,
						farRightDown,
						farDownRight,
					}
					for _, neighbor := range neighbors {
						if neighbor.row < 50 && neighbor.row >= 0 && neighbor.col < 50 && neighbor.col >= 0 {
							neighborPosn := 50*neighbor.row + neighbor.col
							if !visited[neighborPosn] {
								visited[neighborPosn] = true
								bfs.Enqueue(50*neighbor.row + neighbor.col)
							}
						}
					}
				}
				hops++
			}
		}
		return dp[knightPosnIdx][pawnPosnIdx]
	}

	// Now we can efficiently find the distance from any point to any other point - time for minimax
	solsMin := make([][]int, len(boardPosns))
	solsMax := make([][]int, len(boardPosns))
	for i := range solsMin {
		solsMin[i] = make([]int, 1<<len(positions))
		solsMax[i] = make([]int, 1<<len(positions))
		for j := range solsMin[i] {
			solsMin[i][j] = -1
			solsMax[i][j] = -1
		}
	}
	var minimizer func(knightPosnIdx int, pawnsPresentBitMask int) int
	var maximizer func(knightPosnIdx int, pawnsPresentBitMask int) int

	// Define minimizer function
	minimizer = func(knightPosnIdx int, pawnsPresentBitMask int) int {
		if solsMin[knightPosnIdx][pawnsPresentBitMask] == -1 {
			// Need to solve this problem
			if pawnsPresentBitMask == 0 {
				// No pawns left
				solsMin[knightPosnIdx][pawnsPresentBitMask] = 0
			} else {
				// See which pawns are present
				pawnsPresent := []int{}
				for i := range positions {
					if (1<<i)&pawnsPresentBitMask > 0 {
						pawnsPresent = append(pawnsPresent, i)
					}
				}
				record := math.MaxInt32
				for _, pawnIdx := range pawnsPresent {
					// Try taking this knight first
					newPawnsBitMask := pawnsPresentBitMask ^ (1 << pawnIdx)
					// Pawn index offset by 1 in boardPosns
					movesToTakeFirst := dist(knightPosnIdx, pawnIdx+1)
					// Move on to subproblem
					record = min(record, movesToTakeFirst+maximizer(pawnIdx+1, newPawnsBitMask))
				}
				solsMin[knightPosnIdx][pawnsPresentBitMask] = record
			}
		}
		return solsMin[knightPosnIdx][pawnsPresentBitMask]
	}

	// Define maximizer function
	maximizer = func(knightPosnIdx int, pawnsPresentBitMask int) int {
		if solsMax[knightPosnIdx][pawnsPresentBitMask] == -1 {
			// Need to solve this problem
			if pawnsPresentBitMask == 0 {
				// No pawns left
				solsMax[knightPosnIdx][pawnsPresentBitMask] = 0
			} else {
				// See which pawns are present
				pawnsPresent := []int{}
				for i := range positions {
					if (1<<i)&pawnsPresentBitMask > 0 {
						pawnsPresent = append(pawnsPresent, i)
					}
				}
				record := math.MinInt32
				for _, pawnIdx := range pawnsPresent {
					// Try taking this knight first
					newPawnsBitMask := pawnsPresentBitMask ^ (1 << pawnIdx)
					// Pawn index offset by 1 in boardPosns
					movesToTakeFirst := dist(knightPosnIdx, pawnIdx+1)
					// Move on to subproblem
					record = max(record, movesToTakeFirst+minimizer(pawnIdx+1, newPawnsBitMask))
				}
				solsMax[knightPosnIdx][pawnsPresentBitMask] = record
			}
		}
		return solsMax[knightPosnIdx][pawnsPresentBitMask]
	}

	// Solve problem
	pawnsPresent := (1 << len(positions)) - 1 // 111..1 for all knights
	return maximizer(0, pawnsPresent)
}
