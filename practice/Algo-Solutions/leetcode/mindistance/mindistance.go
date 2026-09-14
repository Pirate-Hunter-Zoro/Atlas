package mindistance

/*
Given two strings word1 and word2, return the minimum number of operations required to convert word1 to word2.

You have the following three operations permitted on a word:
- Insert a character
- Delete a character
- Replace a character

Link:
https://leetcode.com/problems/edit-distance/
*/
func minDistance(word1 string, word2 string) int {
	sols := make([][]int, len(word1)+1)
	for i := range len(sols) {
		sols[i] = make([]int, len(word2)+1)
	}
	// Base cases
	for i := range len(sols[0]) {
		if i > 0 {
			sols[0][i] = sols[0][i-1] + 1
		}
	}
	for j := range len(sols) {
		if j > 0 {
			sols[j][0] = sols[j-1][0] + 1
		}
	}

	// Now solve
	for i := 1; i <= len(word1); i++ {
		for j := 1; j <= len(word2); j++ {
			diagonal := sols[i-1][j-1]
			if word1[i-1] != word2[j-1] {
				// Cannot match so must replace
				diagonal += 1
			}
			left := sols[i][j-1] + 1
			top := sols[i-1][j] + 1
			sols[i][j] = min(diagonal, min(left, top))
		}
	}
	return sols[len(sols)-1][len(sols[0])-1]
}
