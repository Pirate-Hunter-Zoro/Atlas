package minimumdeletions

import "math"

/*
You are given a string word and an integer k.

We consider word to be k-special if |freq(word[i]) - freq(word[j])| <= k for all indices i and j in the string.

Here, freq(x) denotes the frequency of the character x in word, and |y| denotes the absolute value of y.

Return the minimum number of characters you need to delete to make word k-special.

Link:
https://leetcode.com/problems/minimum-deletions-to-make-string-k-special/description/?envType=daily-question&envId=2025-06-21
*/
func minimumDeletions(word string, k int) int {
	frequencies := make(map[byte]int)
	for _, c := range word {
		if _, ok := frequencies[byte(c)]; !ok {
			frequencies[byte(c)] = 0
		}
		frequencies[byte(c)]++
	}

	// Whatever answer we get, some character will have the smallest frequency
	// To achieve a k-special string in the minimum number of deletions, we will NOT delete any instances of that character
	record := math.MaxInt
	for c, freq := range frequencies {
		// Assume that c is in the end going to be the character with the smallest frequency
		deletions := 0
		for otherC, otherFreq := range frequencies {
			if otherC != c {
				if otherFreq < freq {
					// Gotta delete all of the other character
					deletions += otherFreq
				} else if otherFreq-k > freq {
					// Gotta delete some of the other character
					deletions += otherFreq - (freq + k)
				}
			}
		}
		record = min(record, deletions)
	}

	return record
}
