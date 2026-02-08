package datastructures

type TrieNode struct {
	children map[rune]*TrieNode
	id int
}

func NewTrie() *TrieNode {
	return &TrieNode{
		children: make(map[rune]*TrieNode),
		id: -1, // No strings end here
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