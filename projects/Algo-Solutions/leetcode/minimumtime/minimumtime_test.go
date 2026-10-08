package minimumtime

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinimumTime(t *testing.T) {
	type input struct {
		n         int
		relations [][]int
		time      []int
	}
	inputs := []input{
		{3, [][]int{{1, 3}, {2, 3}}, []int{3, 2, 5}},
		{5, [][]int{{1, 5}, {2, 5}, {3, 5}, {3, 4}, {4, 5}}, []int{1, 2, 3, 4, 5}},
	}

	expectedOutputs := []int{
		8,
		12,
	}

	f := func(i input) int {
		return minimumTime(i.n, i.relations, i.time)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
