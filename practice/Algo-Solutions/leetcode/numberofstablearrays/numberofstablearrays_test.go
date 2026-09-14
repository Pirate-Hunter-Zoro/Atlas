package numberofstablearrays

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumberOfStableArrays(t *testing.T) {
	type input struct {
		zero  int
		one   int
		limit int
	}
	inputs := []input{
		{1, 1, 2},
		{1, 2, 1},
		{3, 3, 2},
		{1, 2, 3},
		{1, 3, 1},
		{1, 4, 2},
	}

	expectedOutputs := []int{
		2,
		1,
		14,
		3,
		0,
		1,
	}

	f := func(i input) int {
		return numberOfStableArrays(i.zero, i.one, i.limit)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
