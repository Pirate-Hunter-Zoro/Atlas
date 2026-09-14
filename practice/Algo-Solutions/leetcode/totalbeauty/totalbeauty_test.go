package totalbeauty

import (
	"algo-solutions/testutil"
	"testing"
)

func TestTotalBeauty(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1,2,3}},
		{[]int{4,6}},
	}

	expected_outputs := []int{
		10,
		12,
	}

	f := func(i input) int {
		return totalBeauty(i.nums)
	}

	testutil.RunTestHelper(t, f, inputs, expected_outputs)
}