package reachablenodes

import (
	"algo-solutions/testutil"
	"testing"
)

func TestReachableNodes(t *testing.T) {
	type input struct {
		edges    [][]int
		maxMoves int
		n        int
	}
	inputs := []input{
		{
			[][]int{{0, 1, 10}, {0, 2, 1}, {1, 2, 2}},
			6,
			3,
		},
		{
			[][]int{{0, 1, 4}, {1, 2, 6}, {0, 2, 8}, {1, 3, 1}},
			10,
			4,
		},
		{
			[][]int{{1, 2, 4}, {1, 4, 5}, {1, 3, 1}, {2, 3, 4}, {3, 4, 5}},
			17,
			5,
		},
	}

	expectedOutputs := []int{
		13,
		23,
		1,
	}

	f := func(i input) int {
		return reachableNodes(i.edges, i.maxMoves, i.n)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
