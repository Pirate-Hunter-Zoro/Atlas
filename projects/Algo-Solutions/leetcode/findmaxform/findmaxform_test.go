package findmaxform

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindMaxForm(t *testing.T) {
	type input struct {
		strs []string
		m    int
		n    int
	}
	inputs := []input{
		{[]string{"10", "0001", "111001", "1", "0"}, 5, 3},
		{[]string{"10", "0", "1"}, 1, 1},
	}

	expectedOutputs := []int{
		4,
		2,
	}

	f := func(i input) int {
		return findMaxForm(i.strs, i.m, i.n)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
