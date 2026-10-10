package pathsum

import "algo-solutions/datastructures"

/*
Given the root of a binary tree and an integer targetSum, return all root-to-leaf paths where the sum of the node values in the path equals targetSum.
Each path should be returned as a list of the node values, not node references.

A root-to-leaf path is a path starting from the root and ending at any leaf node.
A leaf is a node with no children.

Link:
https://leetcode.com/problems/path-sum-ii/description/?envType=problem-list-v2&envId=depth-first-search
*/
func pathSum(root *datastructures.TreeNode, targetSum int) [][]int {
	paths := make([][]int, 0)
	if root == nil {
		return paths
	}
	nodeStack := datastructures.NewStack[*datastructures.TreeNode]()
	nodeStack.Push(root)
	currentPath := []int{root.Val}
	runningSum := root.Val
	pushed := make(map[*datastructures.TreeNode]bool)
	pushed[root] = true
	for !nodeStack.Empty() {
		nextNode := nodeStack.Peek()
		if nextNode.Left == nil && nextNode.Right == nil {
			// Leaf node - check if the path sum equals targetSum
			if runningSum == targetSum {
				currentPathCopy := make([]int, len(currentPath))
				copy(currentPathCopy, currentPath)
				paths = append(paths, currentPathCopy)
			}
			// Regardless, we now need to backtrack
			runningSum -= nextNode.Val
			currentPath = currentPath[:len(currentPath)-1]
			nodeStack.Pop()
		} else {
			// Not a leaf node - see if the left or right child needs to be processed
			pushedChildren := false
			if nextNode.Left != nil {
				// Try pushing the left child first
				if _, ok := pushed[nextNode.Left]; !ok {
					nodeStack.Push(nextNode.Left)
					pushed[nextNode.Left] = true
					runningSum += nextNode.Left.Val
					currentPath = append(currentPath, nextNode.Left.Val)
					pushedChildren = true
				}
			}
			if !pushedChildren && nextNode.Right != nil {
				// Then try pushing the right child
				if _, ok := pushed[nextNode.Right]; !ok {
					nodeStack.Push(nextNode.Right)
					pushed[nextNode.Right] = true
					runningSum += nextNode.Right.Val
					currentPath = append(currentPath, nextNode.Right.Val)
					pushedChildren = true
				}
			}
			if !pushedChildren {
				// Both children have been processed - backtrack
				runningSum -= nextNode.Val
				currentPath = currentPath[:len(currentPath)-1]
				nodeStack.Pop()
			}
		}
	}

	return paths
}
