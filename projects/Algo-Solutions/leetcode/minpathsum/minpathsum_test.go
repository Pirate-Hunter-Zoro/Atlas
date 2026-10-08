package minpathsum

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinPathSum(t *testing.T) {
	type input struct {
		grid [][]int
	}
	inputs := []input{
		{[][]int{{1, 3, 1}, {1, 5, 1}, {4, 2, 1}}},
		{[][]int{{1, 2, 3}, {4, 5, 6}}},
	}

	expectedOutputs := []int{
		7,
		12,
	}

	f := func(i input) int {
		return minPathSum(i.grid)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
