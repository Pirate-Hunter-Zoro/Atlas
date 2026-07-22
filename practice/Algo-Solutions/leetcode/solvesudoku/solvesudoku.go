package solvesudoku

import (
	"algo-solutions/datastructures"
	"log"
	"maps"
)

/*
Write a program to solve a Sudoku puzzle by filling the empty cells.

A sudoku solution must satisfy all of the following rules:
- Each of the digits 1-9 must occur exactly once in each row.
- Each of the digits 1-9 must occur exactly once in each column.
- Each of the digits 1-9 must occur exactly once in each of the 9 3x3 sub-boxes of the grid.
The '.' character indicates empty cells.

Link:
https://leetcode.com/problems/sudoku-solver/description/
*/
type variable struct {
	values    map[byte]bool
	neighbors []*variable
}

func solveSudoku(boardProblem [][]byte) {
	variableGrid := make([][]*variable, 9)
	for i := range variableGrid {
		variableGrid[i] = make([]*variable, 9)
		for j := range variableGrid[i] {
			variableGrid[i][j] = &variable{}
			variableGrid[i][j].values = make(map[byte]bool)
			if boardProblem[i][j] == '.' {
				for k := 1; k <= 9; k++ {
					// This is a variable that can take on any of the values 1-9 (so far as we can tell right now)
					key := byte(k + '0')
					variableGrid[i][j].values[key] = true
				}
			} else {
				variableGrid[i][j].values[boardProblem[i][j]] = true
			}
		}
	}

	for i := range 9 {
		for j := range 9 {
			assignVars(i, j, variableGrid)
		}
	}

	// Now perform ac3 from all the singleton variables - that'll get rid of some values to start
	for i := range variableGrid {
		for j := range variableGrid[i] {
			if len(variableGrid[i][j].values) == 1 {
				// This is a singleton variable - perform ac3 on it (don't worry about the return on it - we don't need to restore anything and we're assuming the puzzle IS possible to solve so we won't be messed up here)
				ac3(variableGrid[i][j])
			}
		}
	}

	recSudokuSolver(0, 0, variableGrid)
	for i := range variableGrid {
		for j := range variableGrid[i] {
			for k := range variableGrid[i][j].values {
				// There should only be one value in the map
				if len(variableGrid[i][j].values) != 1 {
					log.Fatalf("Cell (%d, %d) has non-singleton domain: %v", i, j, variableGrid[i][j].values)
				}
				boardProblem[i][j] = k
				break
			}
		}
	}
}

func recSudokuSolver(row, col int, variableGrid [][]*variable) bool {
	if row == 9 {
		return true
	} else {
		v := variableGrid[row][col]
		if len(v.values) == 1 {
			// Already solved. Just move to next cell.
			nextRow := row
			nextCol := col
			if nextCol == 8 {
				nextRow++
				nextCol = 0
			} else {
				nextCol++
			}
			return recSudokuSolver(nextRow, nextCol, variableGrid)
		}
		for k := range v.values {
			valuesCopy := make(map[byte]bool)
			maps.Copy(valuesCopy, v.values)
			// Assign this value to the variable - which means removing all other possible values
			v.values = make(map[byte]bool)
			v.values[k] = true
			nextRow := row
			nextCol := col
			if col == 8 {
				nextRow++
				nextCol = 0
			} else {
				nextCol++
			}
			ac3Passed, restoreVars := ac3(v)
			if ac3Passed && recSudokuSolver(nextRow, nextCol, variableGrid) {
				return true
			} else {
				for v2, v2Restore := range restoreVars {
					// Restore the values of the variables
					v2.values = v2Restore
				}
				// Restore the values of the current variable
				v.values = valuesCopy
				// But the value we just tried for our current variable will not work, so remove it
				delete(v.values, k)
			}
		}
		return false
	}
}

func assignVars(row, col int, variableGrid [][]*variable) {
	// Find all the other variables that will be affected by the current variable
	for c := range 9 {
		if col != c {
			variableGrid[row][col].neighbors = append(variableGrid[row][col].neighbors, variableGrid[row][c])
		}
	}
	for r := range 9 {
		if row != r {
			variableGrid[row][col].neighbors = append(variableGrid[row][col].neighbors, variableGrid[r][col])
		}
	}
	blockRowIdx := (row / 3) * 3
	blockColIdx := (col / 3) * 3
	for rOffset := range 3 {
		for cOffset := range 3 {
			rIdx := blockRowIdx + rOffset
			cIdx := blockColIdx + cOffset
			if rIdx != row || cIdx != col {
				variableGrid[row][col].neighbors = append(variableGrid[row][col].neighbors, variableGrid[rIdx][cIdx])
			}
		}
	}
}

type arc struct {
	firstVar  *variable
	secondVar *variable
}

func ac3(v *variable) (bool, map[*variable]map[byte]bool) {
	restoreVars := make(map[*variable]map[byte]bool) // pointer to a struct is hashable because it's an underlying integer
	restoreVars[v] = make(map[byte]bool)
	maps.Copy(restoreVars[v], v.values)
	arcQueue := datastructures.NewQueue[*arc]()
	for _, otherV := range v.neighbors {
		arcQueue.Enqueue(&arc{firstVar: v, secondVar: otherV})
	}
	for !arcQueue.Empty() {
		thisArc := arcQueue.Dequeue()
		first := thisArc.firstVar
		second := thisArc.secondVar
		if _, ok := restoreVars[second]; !ok {
			restoreVars[second] = make(map[byte]bool)
			maps.Copy(restoreVars[second], second.values)
		}
		if removeInconsistentValues(thisArc) {
			// If something ran out of values, we're done - false
			if len(second.values) == 0 {
				return false, restoreVars
			}
			for _, neighbor := range second.neighbors {
				if neighbor != first {
					arcQueue.Enqueue(&arc{firstVar: second, secondVar: neighbor})
				}
			}
		}
	}

	return true, restoreVars // Even if ac3 works, we may not have a solution when we try to solve later variables
}

func removeInconsistentValues(someArc *arc) bool {
	first := someArc.firstVar
	second := someArc.secondVar
	removed := false
	if len(first.values) == 1 {
		// That's going to constrain second variable's values
		for v := range first.values {
			// (There will only be one value in the map)
			if _, ok := second.values[v]; ok {
				removed = true
				delete(second.values, v)
			}
		}
	}
	return removed
}
