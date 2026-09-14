package ladderlength

import "algo-solutions/datastructures"

/*
A transformation sequence from word beginWord to word endWord using a dictionary wordList is a sequence of words beginWord -> s1 -> s2 -> ... -> sk such that:
- Every adjacent pair of words differs by a single letter.
- Every sᵢ for 1 <= i <= k is in wordList. Note that beginWord does not need to be in wordList.
- sₖ == endWord

Given two words, beginWord and endWord, and a dictionary wordList, return the number of words in the shortest transformation sequence from beginWord to endWord, or 0 if no such sequence exists.

Link:
https://leetcode.com/problems/word-ladder/description/
*/
func ladderLength(beginWord string, endWord string, wordList []string) int {
	wordSet := make(map[string]bool)
	for _, word := range wordList {
		wordSet[word] = true
	}
	if _, ok := wordSet[endWord]; !ok {
		// No way to get to the end word
		return 0
	} else {
		// BFS - so we need to make our graph
		visited := make(map[string]bool)
		graph := make(map[string][]string)
		for _, word := range wordList {
			graph[word] = make([]string, 0)
			// Look at all the other words in the list and see if they are one letter different
			for _, otherWord := range wordList {
				if word != otherWord {
					// Check if they are one letter different
					diffCount := 0
					for i := range len(word) {
						if word[i] != otherWord[i] {
							diffCount++
							if diffCount > 1 {
								break
							}
						}
					}
					if diffCount == 1 {
						// They are one letter different - add the edge to the graph
						graph[word] = append(graph[word], otherWord)
					}
				}
			}
		}
		// Also add the beginWord to the graph
		if _, ok := graph[beginWord]; !ok {
			graph[beginWord] = make([]string, 0)
		}
		for _, word := range wordList {
			if word != beginWord {
				// Check if they are one letter different
				diffCount := 0
				for i := range len(beginWord) {
					if beginWord[i] != word[i] {
						diffCount++
						if diffCount > 1 {
							break
						}
					}
				}
				if diffCount == 1 {
					// They are one letter different - add the edge to the graph
					graph[beginWord] = append(graph[beginWord], word)
				}
			}
		}
		queue := datastructures.NewQueue[string]()
		queue.Enqueue(beginWord)
		depth := 1
		visited[beginWord] = true
		for !queue.Empty() {
			n := queue.Size()
			for range n {
				// Take this element out of the queue and enqueue all of its unvisited neighbors
				word := queue.Dequeue()
				if word == endWord {
					// We found the end word - return the depth
					return depth
				}
				for _, neighbor := range graph[word] {
					if _, ok := visited[neighbor]; !ok {
						// Not visited yet - add it to the queue
						visited[neighbor] = true
						queue.Enqueue(neighbor)
					}
				}
			}
			depth++
		}

		// We never found the end word - return 0
		return 0
	}
}
