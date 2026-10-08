package maximumlength

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaximumLength(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1, 2, 3, 4}},
		{[]int{1, 2, 1, 1, 2, 1, 2}},
		{[]int{1, 3}},
	}
	expectedOutputs := []int{
		4,
		6,
		2,
	}

	f := func(i input) int {
		return maximumLength(i.nums)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
