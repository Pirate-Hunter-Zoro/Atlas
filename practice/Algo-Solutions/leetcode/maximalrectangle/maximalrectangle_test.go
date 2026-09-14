package maximalrectangle

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMaximalRectangle(t *testing.T) {
	type input struct {
		matrix [][]byte
	}
	inputs := []input{
		{matrix: [][]byte{{'1', '0', '1', '0', '0'}, {'1', '0', '1', '1', '1'}, {'1', '1', '1', '1', '1'}, {'1', '0', '0', '1', '0'}}},
		{matrix: [][]byte{{'0'}}},
		{matrix: [][]byte{{'1'}}},
	}

	expectedOutputs := []int{
		6, 0, 1,
	}

	f := func(i input) int {
		return maximalRectangle(i.matrix)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
