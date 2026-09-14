package maxprofitiv

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaxProfitIV(t *testing.T) {
	type input struct {
		k      int
		prices []int
	}
	inputs := []input{
		{2, []int{2, 4, 1}},
		{2, []int{3, 2, 6, 5, 0, 3}},
	}

	expectedOutputs := []int{
		2,
		7,
	}

	f := func(i input) int {
		return maxProfitIV(i.k, i.prices)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
