package mintimetoreach

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinTimeToReach(t *testing.T) {
	type input struct {
		moveTime [][]int
	}
	inputs := []input{
		{[][]int{{0, 4}, {4, 4}}},
		{[][]int{{0, 0, 0}, {0, 0, 0}}},
	}
	expectedOutputs := []int{
		6,
		3,
	}

	f := func(i input) int {
		return minTimeToReach(i.moveTime)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
