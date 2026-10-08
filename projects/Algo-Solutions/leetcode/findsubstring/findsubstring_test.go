package findsubstring

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindSubstring(t *testing.T) {
	type input struct {
		s     string
		words []string
	}
	inputs := []input{
		{"barfoothefoobarman", []string{"foo", "bar"}},
		{"wordgoodgoodgoodbestword", []string{"word", "good", "best", "word"}},
		{"barfoofoobarthefoobarman", []string{"bar", "foo", "the"}},
		{"aaaaaaaaaaaaaa", []string{"aa", "aa"}},
	}

	expectedOutputs := [][]int{
		{0, 9},
		{},
		{6, 9, 12},
		{0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10},
	}

	f := func(i input) []int {
		return findSubstring(i.s, i.words)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
