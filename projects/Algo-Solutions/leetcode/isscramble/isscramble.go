package isscramble

/*
We can scramble a string s to get a string t using the following algorithm:
- If the length of the string is 1, stop.
- If the length of the string is > 1, do the following:
  - Split the string into two non-empty substrings at a random index, i.e., if the string is s, divide it to x and y where s = x + y.
  - Randomly decide to swap the two substrings or to keep them in the same order. i.e., after this step, s may become s = x + y or s = y + x.
  - Apply step 1 recursively on each of the two substrings x and y.

Given two strings s1 and s2 of the same length, return true if s2 is a scrambled string of s1, otherwise, return false.

Link: https://leetcode.com/problems/scramble-string/
*/
func isScramble(s1 string, s2 string) bool {
	isScrambleMemo := make(map[string]map[string]bool)

	return recIsScramble(s1, s2, isScrambleMemo)
}

func recIsScramble(l string, r string, isScrambleMemo map[string]map[string]bool) bool {
	_, ok := isScrambleMemo[l]
	if !ok {
		isScrambleMemo[l] = make(map[string]bool)
		// Trivial base case
		isScrambleMemo[l][l] = true
	}
	_, ok = isScrambleMemo[l][r]
	if !ok {
		// Need to solve this problem
		if len(l) == 1 {
			isScrambleMemo[l][r] = l[0] == r[0]
		} else {
			isScrambleMemo[l][r] = false
			for split := range len(l) - 1 {
				// 'split' is the index of the last character in the left half
				leftHalfL := l[:split+1]
				rightHalfL := l[split+1:]
				leftHalfRSwap := r[:len(rightHalfL)]
				rightHalfRSwap := r[len(rightHalfL):]
				leftHalfRNoSwap := r[:split+1]
				rightHalfRNoSwap := r[split+1:]
				isScrambleMemo[l][r] = isScrambleMemo[l][r] || (recIsScramble(rightHalfL, leftHalfRSwap, isScrambleMemo) && recIsScramble(leftHalfL, rightHalfRSwap, isScrambleMemo))
				isScrambleMemo[l][r] = isScrambleMemo[l][r] || (recIsScramble(leftHalfL, leftHalfRNoSwap, isScrambleMemo) && recIsScramble(rightHalfL, rightHalfRNoSwap, isScrambleMemo))
			}
		}
	}
	return isScrambleMemo[l][r]
}
