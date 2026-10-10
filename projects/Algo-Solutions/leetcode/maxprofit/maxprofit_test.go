package maxprofit

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaxProfit(t *testing.T) {
	type input struct {
		n         int
		present   []int
		future    []int
		hierarchy [][]int
		budget    int
	}
	inputs := []input{
		{2, []int{1, 2}, []int{4, 3}, [][]int{{1, 2}}, 3},
		{2, []int{3, 4}, []int{5, 8}, [][]int{{1, 2}}, 4},
		{3, []int{4, 6, 8}, []int{7, 9, 11}, [][]int{{1, 2}, {1, 3}}, 10},
		{3, []int{5, 2, 3}, []int{8, 5, 6}, [][]int{{1, 2}, {2, 3}}, 7},
	}

	expectedOutputs := []int{
		5,
		4,
		10,
		12,
	}

	f := func(i input) int {
		return maxProfit(i.n, i.present, i.future, i.hierarchy, i.budget)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
