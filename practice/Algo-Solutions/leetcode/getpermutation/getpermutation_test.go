package getpermutation

import (
	"algo-solutions/testutil"
	"testing"
)

func TestGetPermutation(t *testing.T) {
	type input struct {
		n int
		k int
	}
	inputs := []input{
		{3, 3},
		{4, 9},
		{3, 1},
		{2, 2},
	}

	expectedOutputs := []string{
		"213",
		"2314",
		"123",
		"21",
	}

	f := func(i input) string {
		return getPermutation(i.n, i.k)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
