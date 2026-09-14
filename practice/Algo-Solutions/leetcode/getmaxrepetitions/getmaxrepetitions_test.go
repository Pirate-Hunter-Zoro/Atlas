package getmaxrepetitions

import (
	"algo-solutions/testutil"
	"testing"
)

func TestGetMaxRepetitions(t *testing.T) {
	type input struct {
		s1 string
		n1 int
		s2 string
		n2 int
	}
	inputs := []input{
		{"acb", 4, "ab", 2},
		{"acb", 1, "acb", 1},
	}
	expectedOutputs := []int{
		2,
		1,
	}

	f := func(i input) int {
		return getMaxRepetitions(i.s1, i.n1, i.s2, i.n2)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
