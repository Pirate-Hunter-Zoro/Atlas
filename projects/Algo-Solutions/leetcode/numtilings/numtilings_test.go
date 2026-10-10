package numtilings

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumTilings(t *testing.T) {
	type input struct {
		n int
	}
	inputs := []input{
		{3},
		{1},
	}

	expectedOutputs := []int{
		5,
		1,
	}

	f := func(i input) int {
		return numTilings(i.n)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
