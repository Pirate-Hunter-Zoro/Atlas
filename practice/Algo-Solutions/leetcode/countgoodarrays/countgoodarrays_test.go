package countgoodarrays

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCountGoodArrays(t *testing.T) {
	type input struct {
		n int
		m int
		k int
	}
	inputs := []input{
		{3, 2, 1},
		{4, 2, 2},
		{5, 2, 0},
	}
	expectedOutputs := []int{
		4,
		6,
		2,
	}
	f := func(i input) int {
		return countGoodArrays(i.n, i.m, i.k)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
