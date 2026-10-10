package generatetrees

import (
	"algo-solutions/datastructures"
	"algo-solutions/testutil"
	"testing"
)

func TestGenerateTrees(t *testing.T) {
	type input struct {
		n int
	}

	inputs := []input {
		{3},
		{1},
	}

	expected_outputs := [][]*datastructures.TreeNode{
		{
			&datastructures.TreeNode{
				Val: 1,
				Left: nil,
				Right: &datastructures.TreeNode{
					Val: 2,
					Left: nil,
					Right: &datastructures.TreeNode{
						Val: 3,
						Left: nil,
						Right: nil,
					},
				},
			},
			&datastructures.TreeNode{
				Val: 1,
				Left: nil,
				Right: &datastructures.TreeNode{
					Val: 3,
					Left: &datastructures.TreeNode{
						Val: 2,
						Left: nil,
						Right: nil,
					},
					Right: nil,
				},
			},
			&datastructures.TreeNode{
				Val: 2,
				Left: &datastructures.TreeNode{
					Val: 1,
					Left: nil,
					Right: nil,
				},
				Right: &datastructures.TreeNode{
					Val: 3,
					Left: nil,
					Right: nil,
				},
			},
			&datastructures.TreeNode{
				Val: 3,
				Left: &datastructures.TreeNode{
					Val: 1,
					Left: nil,
					Right: &datastructures.TreeNode{
						Val: 2,
						Left: nil,
						Right: nil,
					},
				},
				Right: nil,
			},
			&datastructures.TreeNode{
				Val: 3,
				Left: &datastructures.TreeNode{
					Val: 2,
					Left: &datastructures.TreeNode{
						Val: 1,
						Left: nil,
						Right: nil,
					},
					Right: nil,
				},
				Right: nil,
			},
		},
		{
			&datastructures.TreeNode{
				Val: 1,
				Left: nil,
				Right: nil,
			},
		},
	}

	f := func(i input) []*datastructures.TreeNode {
		return generateTrees(i.n)
	}

	testutil.RunTestHelper(t, f, inputs, expected_outputs)
}