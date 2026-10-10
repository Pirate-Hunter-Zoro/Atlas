package trap

import (
	"algo-solutions/testutil"
	"testing"
)

func TestTrap(t *testing.T) {
	type input struct {
		height []int
	}
	inputs := []input{
		{[]int{0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1}},
		{[]int{4, 2, 0, 3, 2, 5}},
	}

	expectedOutputs := []int{
		6,
		9,
	}

	f := func(i input) int {
		return trap(i.height)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
