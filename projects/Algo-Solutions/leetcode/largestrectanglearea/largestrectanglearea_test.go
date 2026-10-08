package largestrectanglearea

import (
	"algo-solutions/testutil"
	"testing"
)

func TestLargestRectangleArea(t *testing.T) {
	type input struct {
		heights []int
	}
	inputs := []input{
		{heights: []int{2, 1, 5, 6, 2, 3}},
		{heights: []int{2, 4}},
	}

	expectedOutputs := []int{
		10,
		4,
	}

	f := func(i input) int {
		return LargestRectangleArea(i.heights)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
