package longestvalidparentheses

import (
	"algo-solutions/testutil"
	"testing"
)

func TestLongestValidParentheses(t *testing.T) {
	type input struct {
		s string
	}
	inputs := []input{
		{"(()"},
		{")()())"},
		{""},
		{"()(())"},
		{")(())(()()))("},
	}

	expectedOutputs := []int{
		2,
		4,
		0,
		6,
		10,
	}

	f := func(i input) int {
		return longestValidParentheses(i.s)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
