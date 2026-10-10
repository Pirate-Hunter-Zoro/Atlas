package maxprofitii

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaxProfitII(t *testing.T) {
	type input struct {
		prices []int
	}
	inputs := []input{
		{[]int{3, 3, 5, 0, 0, 3, 1, 4}},
		{[]int{1, 2, 3, 4, 5}},
		{[]int{7, 6, 4, 3, 1}},
	}

	expectedOutputs := []int{
		6,
		4,
		0,
	}

	f := func(i input) int {
		return maxProfitII(i.prices)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
