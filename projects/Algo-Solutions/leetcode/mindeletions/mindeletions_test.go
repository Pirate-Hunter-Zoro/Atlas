package mindeletions

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinDeletions(t *testing.T) {
	type input struct {
		s string
	}
	inputs := []input{
		{"aab"},
		{"aaabbbcc"},
		{"ceabaacb"},
	}

	expectedOutputs := []int{
		0,
		2,
		2,
	}

	f := func(i input) int {
		return minDeletions(i.s)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
