package candy

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCandy(t *testing.T) {
	type input struct {
		ratings []int
	}

	inputs := []input{
		{[]int{1, 0, 2}},
		{[]int{1, 2, 2}},
	}

	expectedOutputs := []int{
		5,
		4,
	}

	f := func(i input) int {
		return candy(i.ratings)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
