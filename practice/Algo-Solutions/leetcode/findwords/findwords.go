package findwords

import "sort"

type trieNode struct {
	children  map[byte]*trieNode
	endOfWord bool
}

/*
Given an m x n board of characters and a list of strings words, return all words on the board.

Each word must be constructed from letters of sequentially adjacent cells, where adjacent cells are horizontally or vertically neighboring.

The same letter cell may not be used more than once in a word.

Link:
https://leetcode.com/problems/word-search-ii/
*/
func findWords(board [][]byte, words []string) []string {
	visited := make([][]bool, len(board))
	for i := range board {
		visited[i] = make([]bool, len(board[i]))
		for j := range board[i] {
			visited[i][j] = false
		}
	}

	trieRoot := &trieNode{children: make(map[byte]*trieNode)}
	for _, word := range words {
		// Add the word to the trie
		addToTrie(word, trieRoot)
	}

	foundWords := make(map[string]bool)

	for i := range board {
		for j := range board[i] {
			// Start a DFS from this cell
			dfsWordSearch(board, i, j, trieRoot, "", visited, &foundWords)
		}
	}

	foundWordsList := []string{}
	for word := range foundWords {
		foundWordsList = append(foundWordsList, word)
	}
	sort.SliceStable(foundWordsList, func(i, j int) bool {
		return foundWordsList[i] < foundWordsList[j]
	})
	return foundWordsList
}

func addToTrie(word string, node *trieNode) {
	for i := range word {
		char := word[i]
		_, ok := node.children[char]
		if !ok {
			node.children[char] = &trieNode{children: make(map[byte]*trieNode)}
		}
		node = node.children[char]
	}
	node.endOfWord = true
}

func dfsWordSearch(board [][]byte, i int, j int, node *trieNode, currentWord string, visited [][]bool, foundWords *map[string]bool) {
	if i < 0 || i >= len(board) || j < 0 || j >= len(board[i]) || visited[i][j] {
		return
	}
	char := board[i][j]
	_, ok := node.children[char]
	if !ok {
		// No words in the trie have this prefix
		return
	}
	visited[i][j] = true
	currentWord += string(char)
	node = node.children[char]
	if len(node.children) == 0 || node.endOfWord {
		// We have reached the end of a word
		(*foundWords)[currentWord] = true
	}
	// Now search in all directions
	dfsWordSearch(board, i+1, j, node, currentWord, visited, foundWords)
	dfsWordSearch(board, i-1, j, node, currentWord, visited, foundWords)
	dfsWordSearch(board, i, j+1, node, currentWord, visited, foundWords)
	dfsWordSearch(board, i, j-1, node, currentWord, visited, foundWords)
	visited[i][j] = false
}
