package minjumps

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinJumps(t *testing.T) {
	type input struct {
		arr []int
	}
	inputs := []input{
		{[]int{100, -23, -23, 404, 100, 23, 23, 23, 3, 404}},
		{[]int{7}},
		{[]int{7, 6, 9, 6, 9, 6, 9, 7}},
	}

	expectedOutputs := []int{
		3,
		0,
		1,
	}

	f := func(i input) int {
		return minJumps(i.arr)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
