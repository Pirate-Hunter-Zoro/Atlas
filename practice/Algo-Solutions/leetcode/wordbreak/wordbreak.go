package wordbreak

import (
	"sort"
	"strings"
)

/*
Given a string s and a dictionary of strings wordDict, add spaces in s to construct a sentence where each word is a valid dictionary word.
Return all such possible sentences in any order.

Note that the same word in the dictionary may be reused multiple times in the segmentation.

Link:
https://leetcode.com/problems/word-break-ii/description/
*/
func wordBreak(s string, wordDict []string) []string {
	// Turn the list of words into a set for faster lookup
	wordSet := make(map[string]bool)
	for _, word := range wordDict {
		wordSet[word] = true
	}
	// Now we need to find all the possible sentences
	sols := make(map[int][]string) // Answer the question - given the last n-i characters, what are the possible sentences?
	sols[len(s)] = []string{""}
	for i := len(s) - 1; i >= 0; i-- {
		// We need to find all the possible sentences that can be formed from s[i:]
		for j := i + 1; j <= len(s); j++ {
			// Check if s[i:j] is a word
			_, ok := wordSet[s[i:j]]
			if ok {
				// We can form a word from s[i:j]
				// Now we need to find all the possible sentences that can be formed from s[j:]
				possibleSentences, ok := sols[j]
				if ok {
					// We can form a sentence from s[j:]
					_, ok = sols[i]
					if !ok {
						sols[i] = []string{}
					}
					for _, sentence := range possibleSentences {
						var newSentence strings.Builder
						newSentence.WriteString(s[i:j])
						if sentence != "" {
							newSentence.WriteString(" ")
						}
						// Add the rest of the sentence
						newSentence.WriteString(sentence)
						sols[i] = append(sols[i], newSentence.String())
					}
				}
			}
		}
	}
	sol, ok := sols[0]
	if !ok {
		return []string{}
	}
	sort.SliceStable(sol, func(i, j int) bool {
		return sol[i] < sol[j]
	})
	return sol
}
