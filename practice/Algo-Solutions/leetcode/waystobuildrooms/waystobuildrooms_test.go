package waystobuildrooms

import (
	"algo-solutions/testutil"
	"testing"
)

func TestWaysToBuildRooms(t *testing.T) {
	type input struct {
		prevRoom []int
	}
	inputs := []input{
		{[]int{-1, 0, 1}},
		{[]int{-1, 0, 0, 1, 2}},
	}

	expectedOutputs := []int{
		1,
		6,
	}

	f := func(i input) int {
		return waysToBuildRooms(i.prevRoom)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
