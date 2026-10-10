package maxpathsum

import (
	"algo-solutions/datastructures"
	"math"
)

/*
A path in a binary tree is a sequence of nodes where each pair of adjacent nodes in the sequence has an edge connecting them.
A node can only appear in the sequence at most once.
Note that the path does not need to pass through the root.

The path sum of a path is the sum of the node's values in the path.

Given the root of a binary tree, return the maximum path sum of any non-empty path.

Link:
https://leetcode.com/problems/binary-tree-maximum-path-sum/description/
*/
func maxPathSum(root *datastructures.TreeNode) int {
	// Quick dummy case - if there are no children, we have to include this root
	if root.Left == nil && root.Right == nil {
		return root.Val
	}

	// For every node, store the maximum path if you include only the left, only the right, or both children in their path
	maxAllowLeftOnly := make(map[*datastructures.TreeNode]int)  // Max path achievable from this node down including self if only allowed left child
	maxAllowRightOnly := make(map[*datastructures.TreeNode]int) // Same but right child
	maxAllowBoth := make(map[*datastructures.TreeNode]int)      // Same but allow both

	// Create our bottom down function
	var solveAllowLeftOnly func(node *datastructures.TreeNode) int
	var solveAllowRightOnly func(node *datastructures.TreeNode) int
	var solveAllowBoth func(node *datastructures.TreeNode) int
	solveAllowLeftOnly = func(node *datastructures.TreeNode) int {
		if _, ok := maxAllowLeftOnly[node]; !ok {
			// Need to solve this problem
			record := node.Val
			if node.Left != nil {
				record = max(record,
					// Since this node is included, the left child is allowed to have exactly one of its children
					node.Val+max(solveAllowLeftOnly(node.Left), solveAllowRightOnly(node.Left)),
				)
			}
			maxAllowLeftOnly[node] = record
		}
		return maxAllowLeftOnly[node]
	}
	solveAllowRightOnly = func(node *datastructures.TreeNode) int {
		if _, ok := maxAllowRightOnly[node]; !ok {
			// Need to solve this problem
			record := node.Val
			if node.Right != nil {
				record = max(record,
					// Since this node is included, the right child is allowed to have exactly one of its children
					node.Val+max(solveAllowLeftOnly(node.Right), solveAllowRightOnly(node.Right)),
				)
			}
			maxAllowRightOnly[node] = record
		}
		return maxAllowRightOnly[node]
	}
	solveAllowBoth = func(node *datastructures.TreeNode) int {
		if _, ok := maxAllowBoth[node]; !ok {
			// Need to solve this problem
			bestAchieved := node.Val
			if node.Left != nil {
				bestAchieved += max(
					0,
					max(
						solveAllowLeftOnly(node.Left),
						solveAllowRightOnly(node.Left),
					),
				)
			}
			if node.Right != nil {
				bestAchieved += max(
					0,
					max(
						solveAllowLeftOnly(node.Right),
						solveAllowRightOnly(node.Right),
					),
				)
			}
			maxAllowBoth[node] = bestAchieved
		}
		return maxAllowBoth[node]
	}

	// Now look at all nodes and return the best path value you see
	var findBest func(root *datastructures.TreeNode) int
	findBest = func(root *datastructures.TreeNode) int {
		if root == nil {
			return math.MinInt
		} else if root.Left == nil && root.Right == nil {
			return root.Val
		}
		return max(
			solveAllowBoth(root),
			findBest(root.Left),
			findBest(root.Right),
		)
	}

	return findBest(root)
}
