package coinchange

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCoinChange(t *testing.T) {
	type input struct {
		coins  []int
		amount int
	}
	inputs := []input{
		{[]int{1, 2, 5}, 11},
		{[]int{2}, 3},
		{[]int{1}, 0},
	}
	expectedOutput := []int{
		3,
		-1,
		0,
	}

	f := func(i input) int {
		return coinChange(i.coins, i.amount)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutput)
}
