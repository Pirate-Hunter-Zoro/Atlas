package idealarrays

import (
	"algo-solutions/testutil"
	"testing"
)

func TestIdealArrays(t *testing.T) {
	type input struct {
		n        int
		maxValue int
	}
	inputs := []input{
		{2, 5},
		{5, 3},
		{5878, 2900},
	}

	expectedOutputs := []int{
		10,
		11,
		465040898,
	}

	f := func(i input) int {
		return idealArrays(i.n, i.maxValue)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
