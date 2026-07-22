package numdistinct

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumDistinct(t *testing.T) {
	type input struct {
		s string
		t string
	}
	inputs := []input{
		{"rabbbit", "rabbit"},
		{"babgbag", "bag"},
		{"b", "a"},
	}

	expectedOutputs := []int{
		3,
		5,
		0,
	}

	f := func(i input) int {
		return numDistinct(i.s, i.t)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
