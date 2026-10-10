package findorder

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindOrder(t *testing.T) {
	type input struct {
		numCourses    int
		prerequesites [][]int
	}
	inputs := []input{
		{2, [][]int{{1, 0}}},
		{4, [][]int{{1, 0}, {2, 0}, {3, 1}, {3, 2}}},
		{1, [][]int{}},
	}

	expectedOutputs := [][]int{
		{0, 1},
		{0, 1, 2, 3},
		{0},
	}

	f := func(i input) []int {
		return findOrder(i.numCourses, i.prerequesites)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
