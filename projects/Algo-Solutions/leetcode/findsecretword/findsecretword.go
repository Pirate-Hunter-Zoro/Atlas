package findsecretword

import "math"

type Master struct {
	secretWord     string
	allowedGuesses int
	wordList       map[string]bool
	usedGuesses    int
	wordFound      bool
}

func NewMaster(secretWord string, allowedGuesses int, wordList []string) *Master {
	wordListMap := make(map[string]bool)
	for _, word := range wordList {
		wordListMap[word] = true
	}
	return &Master{
		secretWord:     secretWord,
		allowedGuesses: allowedGuesses,
		wordList:       wordListMap,
		usedGuesses:    0,
		wordFound:      false,
	}
}
func (m *Master) Guess(word string) int {
	m.usedGuesses++
	if _, ok := m.wordList[word]; !ok {
		// Word is not in the list
		return -1
	} else {
		// Return the number of exact matches (value and position) of the guess to the secret word
		if word == m.secretWord {
			m.wordFound = true
			return len(m.secretWord) // All letters match
		} else {
			matchCount := 0
			for i := range m.secretWord {
				if word[i] == m.secretWord[i] {
					matchCount++
				}
			}
			return matchCount
		}
	}
}
func (m *Master) GetString() string {
	if m.usedGuesses > m.allowedGuesses || !m.wordFound {
		return "Either you took too many guesses, or you did not find the secret word."
	} else {
		return "You guessed the secret word correctly."
	}
}

/*
You are given an array of unique strings words where words[i] is six letters long. One word of words was chosen as a secret word.

You are also given the helper object Master. You may call Master.guess(word) where word is a six-letter-long string, and it must be from words. Master.guess(word) returns:
-- -1 if word is not from words, or
-- an integer representing the number of exact matches (value and position) of your guess to the secret word.
-- There is a parameter allowedGuesses for each test case where allowedGuesses is the maximum number of times you can call Master.guess(word).

For each test case, you should call Master.guess with the secret word without exceeding the maximum number of allowed guesses. You will get:

"Either you took too many guesses, or you did not find the secret word." if you called Master.guess more than allowedGuesses times or if you did not call Master.guess with the secret word, or
"You guessed the secret word correctly." if you called Master.guess with the secret word with the number of calls to Master.guess less than or equal to allowedGuesses.
The test cases are generated such that you can guess the secret word with a reasonable strategy (other than using the bruteforce method).

  - // This is the Master's API interface.

  - // You should not implement it, or speculate about its implementation

  - type Master struct {

  - }
    *

  - func (this *Master) Guess(word string) int {}

    Link: https://leetcode.com/problems/guess-the-word/description/?envType=problem-list-v2&envId=game-theory
*/
func findSecretWord(words []string, master *Master) {
	currentGuess := words[0] // Just pick the first word to start with
	charsMatched := master.Guess(currentGuess)
	availableWords := make([]string, 0) // This will hold the words that match the first guess
	// Remove all words that don't match the first guess
	for _, word := range words {
		if word != currentGuess && countMatches(currentGuess, word) == charsMatched {
			// This word matches the number of characters in the same position as the first guess
			availableWords = append(availableWords, word)
		}
	}

	for len(availableWords) > 0 {
		// Pick the next word to guess - try simulating what would happen if we guessed each word in the available words list
		smallestMax := math.MaxInt
		bestWord := ""
		bestGroupings := make(map[int][]string) // Groupings of words by how many characters match with this word
		for _, word := range availableWords {
			groupings := make(map[int][]string) // Group words by how many characters match with this word
			for _, otherWord := range availableWords {
				if word != otherWord {
					// Count how many characters match in the same position
					matches := countMatches(word, otherWord)
					if _, ok := groupings[matches]; !ok {
						groupings[matches] = make([]string, 0)
					}
					groupings[matches] = append(groupings[matches], otherWord)
				}
			}
			// Now we have all the groupings of words by how many characters match with this word
			maxGroupSize := 0
			for _, group := range groupings {
				if len(group) > maxGroupSize {
					maxGroupSize = len(group)
				}
			}
			if maxGroupSize < smallestMax {
				smallestMax = maxGroupSize
				bestWord = word
				bestGroupings = groupings
			}
		}
		// Now we have the best word to guess
		charsMatched = master.Guess(bestWord)
		if _, ok := bestGroupings[charsMatched]; ok {
			availableWords = bestGroupings[charsMatched]
		} else {
			availableWords = make([]string, 0)
		}
	}
}

func countMatches(word1, word2 string) int {
	// Count how many letters match in the same position
	matchCount := 0
	for i := range word1 {
		if word1[i] == word2[i] {
			matchCount++
		}
	}
	return matchCount
}
