package numtrees

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumTrees(t *testing.T) {
	type input struct {
		n int
	}
	inputs := []input{
		{3},
		{1},
	}

	expected_outputs := []int{
		5,
		1,
	}

	f := func(i input) int {
		return numTrees(i.n)
	}

	testutil.RunTestHelper(t, f, inputs, expected_outputs)
}