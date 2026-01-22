package datastructures

import "math"

type TreeNode struct {
	Val   int
	Left  *TreeNode
	Right *TreeNode
}
func NewTreeNode(vals []int) *TreeNode {
	if len(vals) == 0 {
		return nil
	}
	root := &TreeNode{Val: vals[0]}
	queue := []*TreeNode{root}
	i := 1
	for i < len(vals) && len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		if vals[i] != math.MinInt {
			node.Left = &TreeNode{Val: vals[i]}
			queue = append(queue, node.Left)
		}
		i++
		if i < len(vals) && vals[i] != math.MinInt {
			node.Right = &TreeNode{Val: vals[i]}
			queue = append(queue, node.Right)
		}
		i++
	}
	return root
}