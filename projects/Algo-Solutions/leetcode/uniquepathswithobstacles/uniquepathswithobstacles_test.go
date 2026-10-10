package uniquepathswithobstacles

import (
	"algo-solutions/testutil"
	"testing"
)

func TestUniquePathsWithObstacles(t *testing.T) {
	type input struct {
		obstacleGrid [][]int
	}
	inputs := []input{
		{[][]int{{0, 0, 0}, {0, 1, 0}, {0, 0, 0}}},
		{[][]int{{0, 1}, {0, 0}}},
	}

	expectedOutputs := []int{
		2,
		1,
	}

	f := func(i input) int {
		return uniquePathsWithObstacles(i.obstacleGrid)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
