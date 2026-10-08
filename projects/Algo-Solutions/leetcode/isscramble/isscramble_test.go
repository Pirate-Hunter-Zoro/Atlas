package isscramble

import (
	"algo-solutions/testutil"
	"testing"
)

func TestIsScramble(t *testing.T) {
	type input struct {
		s1 string
		s2 string
	}
	inputs := []input{
		{"great", "rgeat"},
		{"abcde", "caebd"},
		{"a", "a"},
	}

	expectedOutputs := []bool{
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return isScramble(i.s1, i.s2)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
