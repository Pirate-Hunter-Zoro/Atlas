package pathsum

import (
	"algo-solutions/datastructures"
	"algo-solutions/testutil"
	"math"
	"testing"
)

func TestPathSum(t *testing.T) {
	type input struct {
		root      *datastructures.TreeNode
		targetSum int
	}
	inputs := []input{
		{datastructures.NewTreeNode([]int{5, 4, 8, 11, math.MinInt, 13, 4, 7, 2, math.MinInt, math.MinInt, 5, 1}), 22},
		{datastructures.NewTreeNode([]int{1, 2, 3}), 5},
		{datastructures.NewTreeNode([]int{1, 2}), 0},
	}

	expectedOutputs := [][][]int{
		{{5, 4, 11, 2}, {5, 8, 4, 5}},
		{},
		{},
	}

	f := func(i input) [][]int {
		return pathSum(i.root, i.targetSum)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
