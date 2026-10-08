package distributecookies

import (
	"algo-solutions/testutil"
	"testing"
)

func TestDistributeCookies(t *testing.T) {
	type input struct {
		cookies []int
		k       int
	}
	inputs := []input{
		{[]int{8, 15, 10, 20, 8}, 2},
		{[]int{6, 1, 3, 2, 2, 4, 1, 2}, 3},
	}
	expectedOutputs := []int{
		31,
		7,
	}

	f := func(i input) int {
		return distributeCookies(i.cookies, i.k)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
