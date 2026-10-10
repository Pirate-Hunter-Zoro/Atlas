package countpalindromes

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCountPalindromes(t *testing.T) {
	type input struct {
		s string
	}
	inputs := []input{
		{"103301"},
		{"0000000"},
		{"9999900000"},
	}
	expectedOutputs := []int{
		2,
		21,
		2,
	}

	f := func(i input) int {
		return countPalindromes(i.s)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
