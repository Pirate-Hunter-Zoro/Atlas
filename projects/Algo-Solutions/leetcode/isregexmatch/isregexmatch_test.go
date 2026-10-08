package isregexmatch

import (
	"algo-solutions/testutil"
	"testing"
)

func TestIsRegexMatch(t *testing.T) {
	type input struct {
		s string
		p string
	}
	inputs := []input{
		{"aa", "a"},
		{"aa", "a*"},
		{"ab", ".*"},
		{"aab", "c*a*b"},
	}

	expectedOutputs := []bool{
		false,
		true,
		true,
		true,
	}

	f := func(i input) bool {
		return isRegexMatch(i.s, i.p)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
