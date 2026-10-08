package findminstep

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindMinStep(t *testing.T) {
	type input struct {
		board string
		hand  string
	}
	inputs := []input{
		{"WRRBBW", "RB"},
		{"WWRRBBWW", "WRBRW"},
		{"G", "GGGGG"},
		{"RBYYBBRRB", "YRBGB"},
	}

	expectedOutputs := []int{
		-1,
		2,
		2,
		3,
	}

	f := func(i input) int {
		return findMinStep(i.board, i.hand)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
