package mintimetoreachii

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinTimeToReachII(t *testing.T) {
	type input struct {
		moveTime [][]int
	}
	inputs := []input{
		{[][]int{{0, 4}, {4, 4}}},
		{[][]int{{0, 0, 0, 0}, {0, 0, 0, 0}}},
	}

	expectedOutputs := []int{
		7,
		6,
	}

	f := func(i input) int {
		return minTimeToReachII(i.moveTime)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
