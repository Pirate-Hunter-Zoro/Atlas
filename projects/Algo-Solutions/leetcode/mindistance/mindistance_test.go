package mindistance

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinDistance(t *testing.T) {
	type input struct {
		word1 string
		word2 string
	}
	inputs := []input{
		{"horse", "ros"},
		{"intention", "execution"},
	}
	expectedOutputs := []int{
		3,
		5,
	}

	f := func(i input) int {
		return minDistance(i.word1, i.word2)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
