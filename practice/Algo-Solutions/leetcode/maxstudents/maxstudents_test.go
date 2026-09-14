package maxstudents

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaxStudents(t *testing.T) {
	type input struct {
		seats [][]byte
	}

	inputs := []input{
		{[][]byte{
			{'#', '.', '#', '#', '.', '#'},
			{'.', '#', '#', '#', '#', '.'},
			{'#', '.', '#', '#', '.', '#'},
		}},
		{[][]byte{
			{'.', '#'},
			{'#', '#'},
			{'#', '.'},
			{'#', '#'},
			{'.', '#'},
		}},
		{[][]byte{
			{'#', '.', '.', '.', '#'},
			{'.', '#', '.', '#', '.'},
			{'.', '.', '#', '.', '.'},
			{'.', '#', '.', '#', '.'},
			{'#', '.', '.', '.', '#'},
		}},
	}

	expectedOutputs := []int{
		4,
		3,
		10,
	}

	f := func(i input) int {
		return maxStudents(i.seats)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
