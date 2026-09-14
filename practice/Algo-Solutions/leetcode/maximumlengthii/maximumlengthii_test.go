package maximumlengthii

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaximumLengthII(t *testing.T) {
	type input struct {
		nums []int
		k    int
	}
	inputs := []input{
		{[]int{1, 2, 3, 4, 5}, 2},
		{[]int{1, 4, 2, 3, 1, 4}, 3},
	}

	expectedOutputs := []int{
		5,
		4,
	}

	f := func(i input) int {
		return maximumLengthII(i.nums, i.k)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
