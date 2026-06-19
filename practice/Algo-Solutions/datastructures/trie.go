package datastructures

import "math"

type TrieNode struct {
	children map[rune]*TrieNode
	id int
	bestIdx int
	bestLen int
}

func NewTrie() *TrieNode {
	return &TrieNode{
		children: make(map[rune]*TrieNode),
		id: -1, // No strings end here
		bestIdx: -1, // Not yet seen any words
		bestLen: math.MaxInt, // Any candidate word will have a length shorter than this one
	}
}

func (root *TrieNode) Insert(word string, id int) {
	// Insert the word into the trie and give it the respective id
	curr := root
	for i, char := range word {
		if _, ok := curr.children[char]; !ok {
			curr.children[char] = NewTrie()
		}
		curr = curr.children[char]
		if i == len(word)-1 {
			curr.id = id // String ends here
		}
	}
}

func (root *TrieNode) InsertSuffix(word string, idx int) {
	// Every word's path includes the root - these will be in the word bank, and whenever a query is passed, the word with the shortest length and respective index that matches the longest suffix with the query word is the one we care about
	// See 'stringIndices' problem
	l := len(word)
	if l < root.bestLen {
		root.bestLen = l
		root.bestIdx = idx
	}
	curr := root
	for i:=l-1; i>=0; i-- {
		c := rune(word[i])
		if _, ok := curr.children[c]; !ok {
			curr.children[c] = NewTrie()
		}
		curr = curr.children[c]
		if l < curr.bestLen {
			// If this node already existed, its record should only be updated if the input word's length is lower than current's bestLen, because words will be inserted lowest index first
			curr.bestLen = l
			curr.bestIdx = idx
		}
	}
}

func (root *TrieNode) Search(word string) int {
	// Return ID of the word in the trie if present
	curr := root
	for i, char := range word {
		if _, ok := curr.children[char]; !ok {
			return -1
		}
		curr = curr.children[char]
		if i == len(word)-1 {
			return curr.id // String ends here
		}
	}
	// Should never reach here
	return -1
}

func (root *TrieNode) SearchSuffix(word string) int {
	// Traverse the path in this trie until you cannot anymore, and output the respective best matched word's index
	// Again, see 'stringIndices' problem
	curr := root
	for i := len(word)-1; i>=0; i-- {
		c := rune(word[i])
		if _, ok := curr.children[c]; !ok {
			break
		} else {
			curr = curr.children[c]
		}
	}
	return curr.bestIdx
}

func (root *TrieNode) SearchNode(char rune, curr *TrieNode) *TrieNode {
	// Return the node corresponding to the char from the current node if it exists, else return nil
	if curr == nil { // Assume search from the root
		curr = root
	} 
	if child, ok := curr.children[char]; ok {
		return child
	} 
	return nil
}

func (root *TrieNode) IsWord(curr *TrieNode) bool {
	return curr != nil && curr.id != -1
}

func (root *TrieNode) GetId() int {
	return root.id
}