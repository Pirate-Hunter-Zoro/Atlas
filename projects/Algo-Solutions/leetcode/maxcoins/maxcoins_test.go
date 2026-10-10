package maxcoins

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaxCoins(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{3, 1, 5, 8}},
		{[]int{1, 5}},
	}
	expectedOutputs := []int{
		167,
		10,
	}

	f := func(i input) int {
		return maxCoins(i.nums)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
