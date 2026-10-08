package removeboxes

import (
	"algo-solutions/testutil"
	"testing"
)

func TestRemoveBoxes(t *testing.T) {
	type input struct {
		boxes []int
	}
	inputs := []input{
		{[]int{1, 3, 2, 2, 2, 3, 4, 3, 1}},
		{[]int{1, 1, 1}},
		{[]int{1}},
		{[]int{1, 2, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 1, 2, 2, 2, 2, 1, 2, 1, 1, 2, 2, 1, 2, 1, 2, 2, 2, 2, 2, 1, 2, 1, 2, 2, 1, 1, 1, 2, 2, 1, 2, 1, 2, 2, 1, 2, 1, 1, 1, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1}},
	}

	expectedOutputs := []int{
		23,
		9,
		1,
		2758,
	}

	f := func(i input) int {
		return removeBoxes(i.boxes)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
