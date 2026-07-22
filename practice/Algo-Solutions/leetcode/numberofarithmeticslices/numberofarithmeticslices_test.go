package numberofarithmeticslices

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumberOfArithmeticSlices(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{2, 4, 6, 8, 10}},
		{[]int{7, 7, 7, 7, 7}},
	}

	expectedOutputs := []int{
		7,
		16,
	}

	f := func(i input) int {
		return numberOfArithmeticSlices(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
