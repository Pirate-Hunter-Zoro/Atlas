package ismatch

/*
Given an input string (s) and a pattern (p), implement wildcard pattern matching with support for '?' and '*' where:
- '?' Matches any single character.
- '*' Matches any sequence of characters (including the empty sequence).

The matching should cover the entire input string (not partial).

Link: https://leetcode.com/problems/wildcard-matching/
*/
func isMatch(s string, p string) bool {
	// Get a couple of edge cases out of the way first...
	if len(p) == 0 {
		return len(s) == 0
	} else if len(s) == 0 {
		for i := 0; i < len(p); i++ {
			if p[i] != '*' {
				return false
			}
		}
		return true
	}

	sols := make([][]bool, len(s)+1)
	for i := 0; i <= len(s); i++ {
		sols[i] = make([]bool, len(p)+1)
	}

	// Empty string matches empty string
	sols[0][0] = true

	// Across the top row - pertains to only matching the empty string with increasing substring lengths of the pattern
	for i := 1; i < len(p); i++ {
		pIdx := i - 1
		sols[0][i] = (p[pIdx] == '*' && sols[0][i-1])
	}
	// The left column is all false by default - which it should be except for the 0-0 cell - an empty pattern cannot match a non-empty string

	// Bottom up solution to solve this problem - top to bottom, left to right
	for i := 1; i <= len(s); i++ {
		for j := 1; j <= len(p); j++ {
			sChar := s[i-1]
			pChar := p[j-1]
			if sChar == pChar || pChar == '?' {
				// Must match
				sols[i][j] = sols[i-1][j-1]
			} else if pChar == '*' {
				// Try matching and consuming '*'
				canMatch := sols[i-1][j-1]
				// Try matching and not consuming '*'
				canMatch = canMatch || sols[i-1][j]
				// Try not matching and consuming '*'
				canMatch = canMatch || sols[i][j-1]
				// Store the result
				sols[i][j] = canMatch
			}
		}
	}

	return sols[len(s)][len(p)]
}
