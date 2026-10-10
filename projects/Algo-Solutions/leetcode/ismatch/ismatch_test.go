package ismatch

import (
	"algo-solutions/testutil"
	"testing"
)

func TestIsMatch(t *testing.T) {
	type input struct {
		s string
		p string
	}
	inputs := []input{
		{"aa", "a"},
		{"aa", "*"},
		{"cb", "?a"},
		{"adceb", "*a*b"},
	}

	expectedOutputs := []bool{
		false,
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return isMatch(i.s, i.p)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
