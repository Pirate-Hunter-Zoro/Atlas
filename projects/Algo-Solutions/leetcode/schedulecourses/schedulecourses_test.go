package schedulecourses

import (
	"algo-solutions/testutil"
	"testing"
)

func TestScheduleCourses(t *testing.T) {
	type input struct {
		courses [][]int
	}
	inputs := []input{
		{[][]int{{100, 200}, {200, 1300}, {1000, 1250}, {2000, 3200}}},
		{[][]int{{1, 2}}},
		{[][]int{{3, 2}, {4, 3}}},
		{[][]int{{5, 5}, {4, 6}, {2, 6}}},
	}

	expectedOutputs := []int{
		3,
		1,
		0,
		2,
	}

	f := func(i input) int {
		return scheduleCourse(i.courses)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
