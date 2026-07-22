package mindeletions

import "sort"

/*
A string s is called good if there are no two different characters in s that have the same frequency.

Given a string s, return the minimum number of characters you need to delete to make s good.

The frequency of a character in a string is the number of times it appears in the string.
For example, in the string "aab", the frequency of 'a' is 2, while the frequency of 'b' is 1.

Link:
https://leetcode.com/problems/minimum-deletions-to-make-character-frequencies-unique/description/
*/
func minDeletions(s string) int {
	// Let us start with mapping frequencies to lists of characters with said frequency
	charToFreq := make(map[byte]int)
	for _, c := range s {
		if _, ok := charToFreq[byte(c)]; !ok {
			charToFreq[byte(c)] = 0
		}
		charToFreq[byte(c)]++
	}
	freqToChars := make(map[int][]byte)
	for c, freq := range charToFreq {
		if _, ok := freqToChars[freq]; !ok {
			freqToChars[freq] = make([]byte, 0)
		}
		freqToChars[freq] = append(freqToChars[freq], c)
	}
	// Note that each frequency can only have one character associated with it, so fill up the highest frequencies you can that you need to
	frequencies := make([]int, 0)
	for freq := range freqToChars {
		frequencies = append(frequencies, freq)
	}
	sort.SliceStable(frequencies, func(i, j int) bool {
		return frequencies[i] > frequencies[j]
	})
	deletions := 0
	nextOpenFreq := frequencies[0] // The next open frequency we can use
	for _, currentFreq := range frequencies {
		nextOpenFreq = min(nextOpenFreq, currentFreq)
		if len(freqToChars[currentFreq]) == 1 {
			// No need to delete any characters with this frequency
			continue
		} else {
			// We need to move all characters except one to the next lower open frequencies
			for len(freqToChars[currentFreq]) > 1 {
				if _, ok := freqToChars[nextOpenFreq]; !ok {
					// We can shove one of the characters with this frequency into the next lower frequency
					if nextOpenFreq > 0 {
						// Store in map
						freqToChars[nextOpenFreq] = make([]byte, 0)
						freqToChars[nextOpenFreq] = append(freqToChars[nextOpenFreq], freqToChars[currentFreq][len(freqToChars[currentFreq])-1])
					}
					// Either way, we need to delete one character from frequency
					freqToChars[currentFreq] = freqToChars[currentFreq][:len(freqToChars[currentFreq])-1]
					deletions += currentFreq - nextOpenFreq
				} else {
					nextOpenFreq--
				}
			}
		}
	}
	return deletions
}
