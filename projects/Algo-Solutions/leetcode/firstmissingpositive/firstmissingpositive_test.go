package firstmissingpositive

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFirstMissingPositive(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1, 2, 0}},
		{[]int{3, 4, -1, 1}},
		{[]int{7, 8, 9, 11, 12}},
	}

	expectedOutputs := []int{
		3,
		2,
		1,
	}

	f := func(i input) int {
		return firstMissingPositive(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
