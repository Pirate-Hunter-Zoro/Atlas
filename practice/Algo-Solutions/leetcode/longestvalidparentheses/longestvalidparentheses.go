package longestvalidparentheses

import "algo-solutions/datastructures"

/*
Given a string containing just the characters '(' and ')', return the length of the longest valid (well-formed) parentheses substring.

Link: https://leetcode.com/problems/longest-valid-parentheses/
*/
func longestValidParentheses(s string) int {
	// Keep a running stack, and once we run into a ')' that has no preceding '(' to match, our running length has to start over
	// In the stack, store the position and actual character (as an integer)
	type charIdx struct {
		posn int
		char byte
	}
	charIdxStack := datastructures.NewStack[charIdx]()
	// Finally keep track of the stretches of the string where we have found a valid substring of parentheses and we'll merge them in the end
	stretches := [][]int{}
	for i := range len(s) {
		char := s[i]
		if char == ')' {
			if !charIdxStack.Empty() && charIdxStack.Peek().char == '(' {
				// preceded by a '('
				prevIdx := charIdxStack.Pop().posn
				if len(stretches) > 0 {
					j := len(stretches) - 1
					prevStretch := stretches[j]
					for j >= 0 && prevStretch[0] > prevIdx && prevStretch[1] < i {
						// wraps around the most recent valid substring of parentheses
						j--
						if j >= 0 {
							prevStretch = stretches[j]
						}
					}
					if j < len(stretches)-1 {
						stretches[j+1] = []int{prevIdx, i}
						stretches = stretches[:j+2]
					} else {
						// no previous wraparounds
						stretches = append(stretches, []int{prevIdx, i})
					}
				} else {
					stretches = append(stretches, []int{prevIdx, i})
				}
			}
		} else {
			// just push the opening parentheses on the stack
			charIdxStack.Push(charIdx{posn: i, char: char})
		}
	}

	// Now go through all of our stretches
	record := 0
	runningLength := 0
	for i, stretch := range stretches {
		if i > 0 && stretches[i-1][1] == stretch[0]-1 {
			// Consecutive to previous stretch
			runningLength += stretch[1] - stretch[0] + 1
		} else {
			// Not consecutive to previous stretch so refresh running length
			runningLength = stretch[1] - stretch[0] + 1
		}
		record = max(record, runningLength)
	}

	return record
}
