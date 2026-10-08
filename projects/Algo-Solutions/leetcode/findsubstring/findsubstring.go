package findsubstring

import "sort"

/*
You are given a string s and an array of strings words.
All the strings of words are of the same length.

A concatenated string is a string that exactly contains all the strings of any permutation of words concatenated.

For example, if words = ["ab","cd","ef"], then "abcdef", "abefcd", "cdabef", "cdefab", "efabcd", and "efcdab" are all concatenated strings.
"acdbef" is not a concatenated string because it is not the concatenation of any permutation of words.
Return an array of the starting indices of all the concatenated substrings in s.
You can return the answer in any order.

Link: https://leetcode.com/problems/substring-with-concatenation-of-all-words/
*/
func findSubstring(s string, words []string) []int {
	// Create a map which will serve as keeping track of the count needed of each word
	wordCounts := make(map[string]int)
	for _, w := range words {
		count, ok := wordCounts[w]
		if !ok {
			wordCounts[w] = 1
		} else {
			wordCounts[w] = count + 1
		}
	}

	l := len(words[0])

	starts := []int{}

	for j := range l {
		i := j
		lastStart := i
		wordsSeen := 0
		currentSeen := make(map[string][]int)
		for i <= len(s)-l {
			word := s[i : i+l]
			countNeeded, ok := wordCounts[word]
			if !ok {
				// Not part of words at all - we must start over
				i += l
				lastStart = i
				wordsSeen = 0
				currentSeen = make(map[string][]int)
			} else {
				// This is an actual word in our list
				placesSeen, ok := currentSeen[word]
				if !ok {
					// We have not seen the word yet
					currentSeen[word] = []int{i}
					wordsSeen++
				} else {
					// We have seen the word
					if len(placesSeen) < countNeeded {
						// We DID need another instance of this word, so keep going
						currentSeen[word] = append(placesSeen, i)
						wordsSeen++
					} else {
						// We did NOT need another instance of this word, so we need to do some removing of previously seen words
						firstSeenIdx := placesSeen[0]
						currentSeen[word] = append(placesSeen, i)
						currentSeen[word] = currentSeen[word][1:]
						lastStart = firstSeenIdx + l
						// All words seen at places before this index need to have those records removed
						for prevWord, places := range currentSeen {
							// Binary search places for the first index greater than firstSeenIdx
							left := 0
							right := len(places)
							for left < right {
								mid := (left + right) / 2
								if places[mid] > firstSeenIdx {
									// Try looking left
									right = mid
								} else {
									// Try looking right
									left = mid + 1
								}
							}
							if left >= len(places) {
								// All occurrences of prevWord no longer count
								wordsSeen -= len(places)
								delete(currentSeen, prevWord)
							} else if left > 0 {
								// Some occurrences of prevWord no longer count
								wordsSeen -= left
								currentSeen[prevWord] = currentSeen[prevWord][left:]
							}
						}
					}
				}
				i += l
			}
			if wordsSeen == len(words) {
				// Found a permutation substring - now just get rid of the first word we saw
				starts = append(starts, lastStart)
				wordsSeen--
				firstWord := s[lastStart : lastStart+l]
				lastStart += l
				if len(currentSeen[firstWord]) == 1 {
					delete(currentSeen, firstWord)
				} else {
					currentSeen[firstWord] = currentSeen[firstWord][1:]
				}
			}
		}
	}

	sort.SliceStable(starts, func(i, j int) bool {
		return starts[i] < starts[j]
	})
	return starts
}
