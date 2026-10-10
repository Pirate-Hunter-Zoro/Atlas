package maximumjumps

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaximumJumps(t *testing.T) {
	type input struct {
		nums   []int
		target int
	}
	inputs := []input{
		{[]int{1, 3, 6, 4, 1, 2}, 2},
		{[]int{1, 3, 6, 4, 1, 2}, 3},
		{[]int{1, 3, 6, 4, 1, 2}, 0},
	}

	expectedOutputs := []int{
		3,
		5,
		-1,
	}

	f := func(i input) int {
		return maximumJumps(i.nums, i.target)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
