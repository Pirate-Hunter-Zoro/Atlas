package catmousegame

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCatMouseGame(t *testing.T) {
	type input struct {
		graph [][]int
	}
	inputs := []input{
		{[][]int{{2, 5}, {3}, {0, 4, 5}, {1, 4, 5}, {2, 3}, {0, 2, 3}}},
		{[][]int{{1, 3}, {0}, {3}, {0, 2}}},
		{[][]int{{2, 3}, {2}, {0, 1}, {0, 4}, {3}}},
	}
	expectedOutputs := []int{
		0,
		1,
		2,
	}
	f := func(i input) int {
		return catMouseGame(i.graph)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
