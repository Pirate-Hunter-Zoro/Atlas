package minimumdifference

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinimumDifference(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{3, 1, 2}},
		{[]int{7, 9, 5, 8, 1, 3}},
	}

	expectedOutputs := []int64{
		-1,
		1,
	}

	f := func(i input) int64 {
		return minimumDifference(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
