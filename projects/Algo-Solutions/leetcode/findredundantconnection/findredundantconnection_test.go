package findredundantconnection

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindRedundantConnection(t *testing.T) {
	type input struct {
		edges [][]int
	}
	inputs := []input{
		{[][]int{{1, 2}, {1, 3}, {2, 3}}},
		{[][]int{{1, 2}, {2, 3}, {3, 4}, {1, 4}, {1, 5}}},
	}
	expectedOutputs := [][]int{
		{2, 3},
		{1, 4},
	}

	f := func(i input) []int {
		return findRedundantConnection(i.edges)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
