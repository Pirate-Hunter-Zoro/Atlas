package stonegamev

/*
There are several stones arranged in a row, and each stone has an associated value which is an integer given in the array stoneValue.

In each round of the game, Alice divides the row into two non-empty rows (i.e. left row and right row), then Bob calculates the value of each row which is the sum of the values of all the stones in this row.
Bob throws away the row which has the maximum value, and Alice's score increases by the value of the remaining row.
If the value of the two rows are equal, Bob lets Alice decide which row will be thrown away.
The next round starts with the remaining row.

The game ends when there is only one stone remaining.
Alice's is initially zero.

Return the maximum score that Alice can obtain.

Link:
https://leetcode.com/problems/stone-game-v/description/
*/
func stoneGameV(stoneValue []int) int {
	// First find the sums of all consecutive subsequences of stones
	sums := make([][]int, len(stoneValue))
	for i := range stoneValue {
		sums[i] = make([]int, len(stoneValue))
		for j := range stoneValue {
			sums[i][j] = 0
		}
		sums[i][i] = stoneValue[i]
		for j := i + 1; j < len(stoneValue); j++ {
			sums[i][j] = sums[i][j-1] + stoneValue[j]
		}
	}
	// Now we are ready to find Alice's maximum possible score
	sols := make([][]int, len(stoneValue))
	for i := range stoneValue {
		sols[i] = make([]int, len(stoneValue))
		for j := range stoneValue {
			sols[i][j] = -1
		}
		// By the rules of the game if there is only one stone left, the game ends, so the score for this subproblem is 0
		sols[i][i] = 0
	}
	return recStoneGameV(stoneValue, 0, len(stoneValue)-1, sums, sols)
}

func recStoneGameV(stoneValue []int, left int, right int, sums [][]int, sols [][]int) int {
	if sols[left][right] == -1 {
		// Need to solve this problem
		// Alice is going to divide the row into two non-empty rows
		record := 0
		for i := left + 1; i <= right; i++ {
			sumLeft := sums[left][i-1]
			sumRight := sums[i][right]
			if sumLeft > sumRight {
				// Bob is going to throw away the left row
				record = max(record, sumRight+recStoneGameV(stoneValue, i, right, sums, sols))
			} else if sumLeft < sumRight {
				// Bob is going to throw away the right row
				record = max(record, sumLeft+recStoneGameV(stoneValue, left, i-1, sums, sols))
			} else {
				// Alice gets to choose which row to throw away
				record = max(record, max(
					sumLeft+recStoneGameV(stoneValue, left, i-1, sums, sols),
					sumRight+recStoneGameV(stoneValue, i, right, sums, sols),
				))
			}
		}
		sols[left][right] = record
	}
	return sols[left][right]
}
