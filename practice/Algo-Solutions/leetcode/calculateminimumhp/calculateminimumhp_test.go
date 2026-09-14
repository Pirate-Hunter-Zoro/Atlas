package calculateminimumhp

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCalculateMinimumHP(t *testing.T) {
	type input struct {
		dungeon [][]int
	}
	inputs := []input{
		{[][]int{{-2, -3, 3}, {-5, -10, 1}, {10, 30, -5}}},
		{[][]int{{0}}},
	}

	expectedOutputs := []int{
		7,
		1,
	}

	f := func(i input) int {
		return calculateMinimumHP(i.dungeon)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
