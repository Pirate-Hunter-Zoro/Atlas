package containsnearbyalmostduplicate

import (
	"algo-solutions/testutil"
	"testing"
)

func TestContainsNearbyAlmostDuplicate(t *testing.T) {
	type input struct {
		nums      []int
		indexDiff int
		valueDiff int
	}
	inputs := []input{
		{[]int{1, 2, 3, 1}, 3, 0},
		{[]int{1, 2, 1, 1}, 1, 0},
		{[]int{1, 5, 9, 1, 5, 9}, 2, 3},
		{[]int{-2, 3}, 2, 5},
		{[]int{-3, 3}, 2, 4},
		{[]int{7, 2, 8}, 2, 1},
	}

	expectedOutputs := []bool{
		true,
		true,
		false,
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return containsNearbyAlmostDuplicate(i.nums, i.indexDiff, i.valueDiff)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
