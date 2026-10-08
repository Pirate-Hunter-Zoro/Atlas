package canpartition

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCanPartition(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1, 5, 11, 5}},
		{[]int{1, 2, 3, 5}},
	}

	expectedOutputs := []bool{
		true,
		false,
	}

	f := func(i input) bool {
		return canPartition(i.nums)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
