package ladderlength

import (
	"algo-solutions/testutil"
	"testing"
)

func TestLadderLength(t *testing.T) {
	type input struct {
		beginWord string
		endWord   string
		wordList  []string
	}
	inputs := []input{
		{"hit", "cog", []string{"hot", "dot", "dog", "lot", "log", "cog"}},
		{"hit", "cog", []string{"hot", "dot", "dog", "lot", "log"}},
	}

	expectedOutputs := []int{
		5,
		0,
	}

	f := func(i input) int {
		return ladderLength(i.beginWord, i.endWord, i.wordList)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
