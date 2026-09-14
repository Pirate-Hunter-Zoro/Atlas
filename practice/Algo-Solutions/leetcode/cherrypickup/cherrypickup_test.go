package cherrypickup

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCherryPickup(t *testing.T) {
	type input struct {
		grid [][]int
	}
	inputs := []input{
		{[][]int{{0, 1, -1}, {1, 0, -1}, {1, 1, 1}}},
		{[][]int{{1, 1, -1}, {1, -1, 1}, {-1, 1, 1}}},
	}

	expectedOutputs := []int{
		5,
		0,
	}

	f := func(i input) int {
		return cherryPickup(i.grid)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
