package numberofpaths

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumberOfPaths(t *testing.T) {
	type input struct {
		grid [][]int
		k    int
	}
	inputs := []input{
		{
			[][]int{{5, 2, 4}, {3, 0, 5}, {0, 7, 2}},
			3,
		},
		{
			[][]int{{0, 0}},
			5,
		},
	}
	expectedOutputs := []int{
		2,
		1,
	}

	f := func(i input) int {
		return numberOfPaths(i.grid, i.k)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
