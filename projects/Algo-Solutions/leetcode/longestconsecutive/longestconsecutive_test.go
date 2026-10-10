package longestconsecutive

import (
	"algo-solutions/testutil"
	"testing"
)

func TestLongestConsecutive(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{100, 4, 200, 1, 3, 2}},
		{[]int{0, 3, 7, 2, 5, 8, 4, 6, 0, 1}},
		{[]int{1, 0, 1, 2}},
		{[]int{1, 2, 0, 1}},
	}

	expectedOutputs := []int{
		4,
		9,
		3,
		3,
	}

	f := func(i input) int {
		return longestConsecutive(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
