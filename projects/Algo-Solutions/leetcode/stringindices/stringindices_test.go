package stringindices

import (
	"algo-solutions/testutil"
	"testing"
)

func TestStringIndices(t *testing.T) {
	type input struct {
		wordsContainer []string
		wordsQuery     []string
	}
	inputs := []input{
		{[]string{"abcd", "bcd", "xbcd"}, []string{"cd", "bcd", "xyz"}},
		{[]string{"abcdefgh", "poiuygh", "ghghgh"}, []string{"gh", "acbfgh", "acbfegh"}},
	}

	expectedOutputs := [][]int{
		{1, 1, 1},
		{2, 0, 2},
	}

	f := func(i input) []int {
		return stringIndices(i.wordsContainer, i.wordsQuery)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
