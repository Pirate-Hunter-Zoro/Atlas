package supereggdrop

import (
	"algo-solutions/testutil"
	"testing"
)

func TestSuperEggDrop(t *testing.T) {
	type input struct {
		n int
		k int
	}

	inputs := []input{
		{n: 1, k: 2},
		{n: 2, k: 6},
		{n: 3, k: 14},
		{n: 1, k: 1},
		{n: 7, k: 5000},
	}

	expectedOutputs := []int{
		2, 3, 4, 1, 13,
	}

	f := func(i input) int {
		return superEggDrop(i.n, i.k)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
