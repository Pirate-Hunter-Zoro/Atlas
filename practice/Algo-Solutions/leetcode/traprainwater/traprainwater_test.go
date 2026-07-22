package traprainwater

import (
	"algo-solutions/testutil"
	"testing"
)

func TestTrapRainWater(t *testing.T) {
	type input struct {
		heightMap [][]int
	}
	inputs := []input{
		{[][]int{{1, 4, 3, 1, 3, 2}, {3, 2, 1, 3, 2, 4}, {2, 3, 3, 2, 3, 1}}},
		{[][]int{{3, 3, 3, 3, 3}, {3, 2, 2, 2, 3}, {3, 2, 1, 2, 3}, {3, 2, 2, 2, 3}, {3, 3, 3, 3, 3}}},
	}

	expectedOutputs := []int{
		4,
		10,
	}

	f := func(i input) int {
		return trapRainWater(i.heightMap)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
