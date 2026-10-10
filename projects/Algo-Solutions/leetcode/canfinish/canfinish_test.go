package canfinish

import (
	"algo-solutions/testutil"
	"testing"
)

func TestCanFinish(t *testing.T) {
	type input struct {
		numCourses    int
		prerequisites [][]int
	}
	inputs := []input{
		{2, [][]int{{1, 0}}},
		{2, [][]int{{1, 0}, {0, 1}}},
	}

	expectedOutputs := []bool{true, false}

	f := func(i input) bool {
		return canFinish(i.numCourses, i.prerequisites)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
