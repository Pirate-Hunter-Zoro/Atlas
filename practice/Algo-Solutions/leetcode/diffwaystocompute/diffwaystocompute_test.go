package diffwaystocompute

import (
	"algo-solutions/testutil"
	"sort"
	"testing"
)

func TestDiffWaysToCompute(t *testing.T) {
	type input struct {
		expression string
	}
	inputs := []input{
		{"2-1-1"},
		{"2*3-4*5"},
	}

	expected_outputs := [][]int{
		{0,2},
		{-34,-14,-10,-10,10},
	}

	f := func(i input) []int {
		sols := diffWaysToCompute(i.expression)
		sort.SliceStable(sols, func(i int, j int) bool {
			return sols[i] < sols[j]
		})
		return sols
	}

	testutil.RunTestHelper(t, f, inputs, expected_outputs)
}