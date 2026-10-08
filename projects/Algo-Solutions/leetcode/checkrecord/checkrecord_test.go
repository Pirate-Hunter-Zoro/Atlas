package checkrecord

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCheckRecord(t *testing.T) {
	type input struct {
		n int
	}
	inputs := []input{
		{2},
		{1},
		{3},
		{10101},
	}

	expectedOutputs := []int{
		8,
		3,
		19,
		183236316,
	}

	f := func(i input) int {
		return checkRecord(i.n)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
