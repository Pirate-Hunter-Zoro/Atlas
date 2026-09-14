package uniquepathsiii

import (
	"algo-solutions/testutil"
	"testing"
)

func TestUniquePathsIII(t *testing.T) {
	type input struct {
		grid [][]int
	}
	inputs := []input{
		{[][]int{{1, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 2, -1}}},
		{[][]int{{1, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 2}}},
		{[][]int{{0, 1}, {2, 0}}},
		{[][]int{{0, 0, 0, 0, 0}, {0, -1, -1, 0, 1}, {0, 0, -1, 0, 2}}},
	}
	expectedOutputs := []int{
		2,
		4,
		0,
		0,
	}

	f := func(i input) int {
		return uniquePathsIII(i.grid)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
