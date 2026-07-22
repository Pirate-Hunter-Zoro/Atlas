package countpalindromes

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

/*
Given a string of digits s, return the number of palindromic subsequences of s having length 5.
Since the answer may be very large, return it modulo 10⁹ + 7.

Note:
A string is palindromic if it reads the same forward and backward.
A subsequence is a string that can be derived from another string by deleting some or no characters without changing the order of the remaining characters.

Link:
https://leetcode.com/problems/count-palindromic-subsequences/description/
*/
func countPalindromes(s string) int {
	str := []byte(s)
	digits := []byte{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
	posns := make(map[byte][]int)
	for i := range s {
		if _, ok := posns[s[i]]; !ok {
			posns[s[i]] = make([]int, 0)
		}
		posns[s[i]] = append(posns[s[i]], i)
	}
	// Count the number of palindromic subsequences of length 5 - note they must be of the form 'abcba'
	total := 0
	for _, a := range digits {
		for _, b := range digits {
			// Count how many palindromes are of the form 'a, b, ANYTHING, b, a'
			prefixCounts := make([]int, len(str))
			// Count how many 'ab' pairs we can form up to each index
			countA := 0
			for i := range str {
				if str[i] == b {
					// Then we can form an 'ab' pair for all occurences of 'a' before this index
					prefixCounts[i] = countA
				}
				if str[i] == a {
					countA = helpermath.ModAdd(countA, 1, leetcode.MOD)
				}
				if i > 0 {
					prefixCounts[i] = helpermath.ModAdd(prefixCounts[i], prefixCounts[i-1], leetcode.MOD)
				}
			}
			// Count how many 'ba' pairs we can form from the end of the string
			suffixCounts := make([]int, len(str))
			countA = 0
			for i := len(str) - 1; i >= 0; i-- {
				if str[i] == b {
					// Then we can form a 'ba' pair for all occurences of 'a' after this index
					suffixCounts[i] = countA
				}
				if str[i] == a {
					countA = helpermath.ModAdd(countA, 1, leetcode.MOD)
				}
				if i < len(str)-1 {
					suffixCounts[i] = helpermath.ModAdd(suffixCounts[i], suffixCounts[i+1], leetcode.MOD)
				}
			}
			// Now we can count the number of palindromic subsequences of the form 'a, b, ANYTHING, b, a'
			for i := range str {
				if i > 1 && i < len(str)-2 {
					// We can form a palindromic subsequence of the form 'a, b, ANYTHING, b, a' if we have at least one 'ab' pair before i and at least one 'ba' pair after i
					total = helpermath.ModAdd(total, helpermath.ModMul(prefixCounts[i-1], suffixCounts[i+1], leetcode.MOD), leetcode.MOD)
				}
			}
		}
	}
	return total
}
