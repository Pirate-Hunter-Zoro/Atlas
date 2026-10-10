package minimumdeletions

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinimumDeletions(t *testing.T) {
	type input struct {
		word string
		k    int
	}
	inputs := []input{
		{"aabcaba", 0},
		{"dabdcbdcdcd", 2},
		{"aaabaaa", 2},
	}

	expectedOutputs := []int{
		3,
		2,
		1,
	}

	f := func(i input) int {
		return minimumDeletions(i.word, i.k)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
