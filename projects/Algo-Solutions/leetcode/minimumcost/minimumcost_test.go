package minimumcost

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinimumCost(t *testing.T) {
	type input struct {
		source   string
		target   string
		original []string
		changed  []string
		cost     []int
	}
	inputs := []input{
		{
			"abcd",
			"acbe",
			[]string{"a", "b", "c", "c", "e", "d"},
			[]string{"b", "c", "b", "e", "b", "e"},
			[]int{2, 5, 5, 1, 2, 20},
		},
		{
			"abcdefgh",
			"acdeeghh",
			[]string{"bcd", "fgh", "thh"},
			[]string{"cde", "thh", "ghh"},
			[]int{1, 3, 5},
		},
		{
			"abcdefgh",
			"addddddd",
			[]string{"bcd", "defgh"},
			[]string{"ddd", "ddddd"},
			[]int{100, 1578},
		},
	}

	expectedOutputs := []int64{
		28,
		9,
		-1,
	}

	f := func(i input) int64 {
		return minimumCost(i.source, i.target, i.original, i.changed, i.cost)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
