package isregexmatch

/*
Given an input string s and a pattern p, implement regular expression matching with support for '.' and '*' where:
- '.' Matches any single character.​​​​
- '*' Matches zero or more of the preceding element.
The matching should cover the entire input string (not partial).

Link:
https://leetcode.com/problems/regular-expression-matching/description/
*/
func isRegexMatch(s string, p string) bool {
	sols := make([][]int, len(s)+1)
	for i := range sols {
		sols[i] = make([]int, len(p)+1)
	}
	sols[0][0] = 2 // Empty string matches empty string

	var f func(i int, j int) bool
	f = func(i int, j int) bool {
		if sols[i][j] == 0 {
			// Need to solve this problem
			// i is index of s, j is index of p

			if i == 0 {
				// String ran out
				if p[j-1] != '*' {
					// No salvaging the mismatch
					return false
				} else {
					// Wipe out the '*' and the previous character before it in p
					match := f(i, j-2)
					if match {
						// match
						sols[i][j] = 2
					} else {
						// mismatch
						sols[i][j] = 1
					}
				}
			} else if j == 0 {
				// Pattern ran out - no salvaging mismatch
				return false
			} else {
				if s[i-1] == p[j-1] {
					// Need to match - recursive path is clear
					match := f(i-1, j-1)
					if match {
						// match
						sols[i][j] = 2
					} else {
						// mismatch
						sols[i][j] = 1
					}
				} else {
					if p[j-1] != '.' && p[j-1] != '*' {
						// mismatch
						sols[i][j] = 1
					} else if p[j-1] == '*' {
						// Consider previous character in p
						if p[j-1-1] == s[i-1] || p[j-1-1] == '.' {
							// CAN match - try using the previous character once, using it more than once, and try just letting the '*' wipe out the previous character
							resUseOnce := f(i-1, j-2)
							resUseMoreThanOnce := f(i-1, j)
							resNoUse := f(i, j-2)
							if resUseOnce || resUseMoreThanOnce || resNoUse {
								// match
								sols[i][j] = 2
							} else {
								// mismatch
								sols[i][j] = 1
							}
						} else {
							// The previous character in p will not help us here
							// Cannot use the '*'
							match := f(i, j-2)
							if match {
								// match
								sols[i][j] = 2
							} else {
								// mismatch
								sols[i][j] = 1
							}
						}
					} else {
						// '.' - and we must try to use it
						match := f(i-1, j-1)
						if match {
							// match
							sols[i][j] = 2
						} else {
							// mismatch
							sols[i][j] = 1
						}
					}
				}
			}
		}
		return sols[i][j] == 2
	}

	return f(len(s), len(p))
}
