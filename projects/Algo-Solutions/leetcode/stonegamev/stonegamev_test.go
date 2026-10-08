package stonegamev

import (
	"algo-solutions/testutil"
	"testing"
)

func TestStoneGameV(t *testing.T) {
	type input struct {
		stoneValue []int
	}
	inputs := []input{
		{[]int{6, 2, 3, 4, 5, 5}},
		{[]int{7, 7, 7, 7, 7, 7, 7}},
		{[]int{4}},
	}
	expectedOutputs := []int{
		18,
		28,
		0,
	}

	f := func(i input) int {
		return stoneGameV(i.stoneValue)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
