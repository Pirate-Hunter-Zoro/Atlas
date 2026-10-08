package uniquepaths

import (
	"algo-solutions/testutil"
	"testing"
)

func TestUniquePaths(t *testing.T) {
	type input struct {
		m int
		n int
	}
	inputs := []input{
		{3, 7},
		{3, 2},
	}

	expectedOutputs := []int{
		28,
		3,
	}

	f := func(i input) int {
		return uniquePaths(i.m, i.n)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
