package splitarray

import (
	"algo-solutions/testutil"
	"testing"
)

func TestSplitArray(t *testing.T) {
	type input struct {
		nums []int
		k    int
	}
	inputs := []input{
		{[]int{7, 2, 5, 10, 8}, 2},
		{[]int{1, 2, 3, 4, 5}, 2},
		{[]int{1, 4, 4}, 3},
	}

	expectedOutputs := []int{
		18,
		9,
		4,
	}

	f := func(i input) int {
		return splitArray(i.nums, i.k)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
