package numdistinct

/*
Given two strings s and t, return the number of distinct subsequences of s which equals t.

The test cases are generated so that the answer fits on a 32-bit signed integer.

Link: https://leetcode.com/problems/distinct-subsequences/
*/
func numDistinct(s string, t string) int {
	// Answer the question - how many different subsequences of s[:i+1] can create t[:j+1]?
	numDistinctMemo := make([][]int, len(s))
	for i := range len(s) {
		numDistinctMemo[i] = make([]int, len(t))
		for j := range min(i+1, len(t)) {
			numDistinctMemo[i][j] = -1
		}
	}

	return recNumDistinct(s, t, len(s)-1, len(t)-1, numDistinctMemo)
}

func recNumDistinct(s string, t string, sIdx int, tIdx int, numDistinctMemo [][]int) int {
	if numDistinctMemo[sIdx][tIdx] == -1 {
		// Need to solve this problem
		numDistinctMemo[sIdx][tIdx] = 0
		if sIdx >= tIdx {
			// There is actually a possibility for subsequences to occur
			if sIdx == 0 && s[sIdx] == t[tIdx] {
				numDistinctMemo[sIdx][tIdx]++
			} else if tIdx == 0 && sIdx > 0 {
				// Then count all the times this single character in t was matched with prior characters in s
				numDistinctMemo[sIdx][tIdx] += recNumDistinct(s, t, sIdx-1, tIdx, numDistinctMemo)
				if s[sIdx] == t[tIdx] {
					numDistinctMemo[sIdx][tIdx]++
				}
			} else if sIdx > 0 && tIdx > 0 {
				// Multiple characters from both substrings
				if s[sIdx] == t[tIdx] {
					// Try matching these two characters
					numDistinctMemo[sIdx][tIdx] += recNumDistinct(s, t, sIdx-1, tIdx-1, numDistinctMemo)
				}
				// Try not matching these two characters
				numDistinctMemo[sIdx][tIdx] += recNumDistinct(s, t, sIdx-1, tIdx, numDistinctMemo)
			}
		}
	}
	return numDistinctMemo[sIdx][tIdx]
}
