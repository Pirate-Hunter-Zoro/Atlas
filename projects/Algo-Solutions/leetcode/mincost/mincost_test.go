package mincost

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinCost(t *testing.T) {
	type input struct {
		maxTime     int
		edges       [][]int
		passingFees []int
	}
	inputs := []input{
		{30, [][]int{{0, 1, 10}, {1, 2, 10}, {2, 5, 10}, {0, 3, 1}, {3, 4, 10}, {4, 5, 15}}, []int{5, 1, 2, 20, 20, 3}},
		{29, [][]int{{0, 1, 10}, {1, 2, 10}, {2, 5, 10}, {0, 3, 1}, {3, 4, 10}, {4, 5, 15}}, []int{5, 1, 2, 20, 20, 3}},
		{25, [][]int{{0, 1, 10}, {1, 2, 10}, {2, 5, 10}, {0, 3, 1}, {3, 4, 10}, {4, 5, 15}}, []int{5, 1, 2, 20, 20, 3}},
		{10, [][]int{{0, 1, 2}, {0, 2, 1}, {0, 3, 10}, {1, 3, 2}, {3, 2, 2}, {4, 3, 1}}, []int{1, 1, 3, 2, 1}},
	}
	expectedOutputs := []int{
		11,
		48,
		-1,
		5,
	}

	f := func(i input) int {
		return minCost(i.maxTime, i.edges, i.passingFees)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
