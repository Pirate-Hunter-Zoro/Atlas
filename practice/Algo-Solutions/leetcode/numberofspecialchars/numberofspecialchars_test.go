package numberofspecialchars

import (
	"algo-solutions/testutil"
	"testing"
)

func TestNumberOfSpecialChars(t *testing.T) {
	type input struct {
		word string
	}
	inputs := []input{
		{"aaAbcBC"},
		{"abc"},
		{"AbBCab"},
	}

	expectedOutputs := []int{
		3,
		0,
		0,
	}

	f := func(i input) int {
		return numberOfSpecialChars(i.word)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
