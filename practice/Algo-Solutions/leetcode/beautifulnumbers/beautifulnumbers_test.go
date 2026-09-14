package beautifulnumbers

import (
	"algo-solutions/testutil"
	"testing"
)

func TestBeautifulNumbers(t *testing.T) {
	type input struct {
		l int
		r int
	}
	inputs := []input{
		{10, 20},
		{1, 15},
		{20, 26},
		{20, 100},
	}

	expectedOutputs := []int{
		2,
		10,
		2,
		15,
	}

	f := func(i input) int {
		return beautifulNumbers(i.l, i.r)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
