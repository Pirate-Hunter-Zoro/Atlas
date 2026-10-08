package connecttwogroups

import (
	"algo-solutions/testutil"
	"testing"
)

func TestConnectTwoGroups(t *testing.T) {
	type input struct {
		cost [][]int
	}

	inputs := []input{
		{[][]int{{15, 96}, {36, 2}}},
		{[][]int{{1, 3, 5}, {4, 1, 1}, {1, 5, 3}}},
		{[][]int{{2, 5, 1}, {3, 4, 7}, {8, 1, 2}, {6, 2, 4}, {3, 8, 8}}},
	}

	expectedOutputs := []int{
		17,
		4,
		10,
	}

	f := func(i input) int {
		return connectTwoGroups(i.cost)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
