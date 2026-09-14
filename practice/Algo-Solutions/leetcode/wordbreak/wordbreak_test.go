package wordbreak

import (
	"algo-solutions/testutil"
	"testing"
)

func TestWordBreak(t *testing.T) {
	type input struct {
		s        string
		wordDict []string
	}
	inputs := []input{
		{"catsanddog", []string{"cat", "cats", "and", "sand", "dog"}},
		{"pineapplepenapple", []string{"apple", "pen", "applepen", "pine", "pineapple"}},
		{"catsandog", []string{"cats", "dog", "sand", "and", "cat"}},
	}

	expectedOutputs := [][]string{
		{"cat sand dog", "cats and dog"},
		{"pine apple pen apple", "pine applepen apple", "pineapple pen apple"},
		{},
	}

	f := func(i input) []string {
		return wordBreak(i.s, i.wordDict)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
