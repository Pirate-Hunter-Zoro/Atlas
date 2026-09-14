package findwords

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindWords(t *testing.T) {
	type input struct {
		board [][]byte
		words []string
	}
	inputs := []input{
		{[][]byte{
			{'o', 'a', 'a', 'n'},
			{'e', 't', 'a', 'e'},
			{'i', 'h', 'k', 'r'},
			{'i', 'f', 'l', 'v'},
		}, []string{"oat", "oath", "pea", "eat", "rain"}},
		{[][]byte{
			{'a', 'b'},
			{'c', 'd'},
		}, []string{"abcb"}},
	}

	expectedOutputs := [][]string{
		{"eat", "oat", "oath"},
		{},
	}

	f := func(i input) []string {
		return findWords(i.board, i.words)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)

}
