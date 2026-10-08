package stringindices

import "algo-solutions/datastructures"

/*
You are given two arrays of strings wordsContainer and wordsQuery.

For each wordsQuery[i], you need to find a string from wordsContainer that has the longest common suffix with wordsQuery[i].
If there are two or more strings in wordsContainer that share the longest common suffix, find the string that is the smallest in length.
If there are two or more such strings that have the same smallest length, find the one that occurred earlier in wordsContainer.

Return an array of integers ans, where ans[i] is the index of the string in wordsContainer that has the longest common suffix with wordsQuery[i].

Link:
https://leetcode.com/problems/longest-common-suffix-queries/description/?envType=daily-question&envId=2026-05-27
*/
func stringIndices(wordsContainer []string, wordsQuery []string) []int {
	indices := make([]int, len(wordsQuery))
	trie := datastructures.NewTrie()
	for i := range wordsContainer {
		trie.InsertSuffix(wordsContainer[i], i)
	}

	// Now query
	for j := range wordsQuery {
		indices[j] = trie.SearchSuffix(wordsQuery[j])
	}

	return indices
}
