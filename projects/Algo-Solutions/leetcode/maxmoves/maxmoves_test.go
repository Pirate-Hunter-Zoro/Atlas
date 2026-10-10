package maxmoves

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaxMoves(t *testing.T) {
	type input struct {
		kx        int
		ky        int
		positions [][]int
	}
	inputs := []input{
		{1, 1, [][]int{{0, 0}}},
		{0, 2, [][]int{{1, 1}, {2, 2}, {3, 3}}},
		{0, 0, [][]int{{1, 2}, {2, 4}}},
		{49, 49, [][]int{{0, 0}}},
	}

	expectedOutputs := []int{
		4,
		8,
		3,
		34,
	}

	f := func(i input) int {
		return maxMoves(i.kx, i.ky, i.positions)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
