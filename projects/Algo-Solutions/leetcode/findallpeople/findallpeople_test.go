package findallpeople

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindAllPeople(t *testing.T) {
	type input struct {
		meetings    [][]int
		firstPerson int
	}
	inputs := []input{
		{[][]int{{1, 2, 5}, {2, 3, 8}, {1, 5, 10}}, 1},
		{[][]int{{3, 1, 3}, {1, 2, 2}, {0, 3, 3}}, 3},
		{[][]int{{3, 4, 2}, {1, 2, 1}, {2, 3, 1}}, 1},
	}

	expectedOutputs := [][]int{
		{0, 1, 2, 3, 5},
		{0, 1, 3},
		{0, 1, 2, 3, 4},
	}

	f := func(i input) []int {
		return findAllPeople(i.meetings, i.firstPerson)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
