package lengthoflis

import (
	"algo-solutions/testutil"
	"testing"
)

func TestLengthOfLIS(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{10, 9, 2, 5, 3, 7, 101, 18}},
		{[]int{0, 1, 0, 3, 2, 3}},
		{[]int{7, 7, 7, 7, 7, 7, 7}},
	}
	expectedOutputs := []int{
		4,
		4,
		1,
	}

	f := func(i input) int {
		return lengthOfLIS(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}

func TestLengthOfLISFast(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{10, 9, 2, 5, 3, 7, 101, 18}},
		{[]int{0, 1, 0, 3, 2, 3}},
		{[]int{7, 7, 7, 7, 7, 7, 7}},
	}
	expectedOutputs := []int{
		4,
		4,
		1,
	}

	f := func(i input) int {
		return lengthOfLISFast(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
