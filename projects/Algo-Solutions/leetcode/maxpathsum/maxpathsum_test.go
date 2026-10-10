package maxpathsum

import (
	"algo-solutions/datastructures"
	"algo-solutions/testutil"
	"math"
	"testing"
)

func TestMaxPathSum(t *testing.T) {
	type input struct {
		root *datastructures.TreeNode
	}
	inputs := []input{
		{datastructures.NewTreeNode([]int{1, 2, 3})},
		{datastructures.NewTreeNode([]int{-10, 9, 20, math.MinInt, math.MinInt, 15, 7})},
	}

	expectedOutputs := []int{
		6,
		42,
	}

	f := func(i input) int {
		return maxPathSum(i.root)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
