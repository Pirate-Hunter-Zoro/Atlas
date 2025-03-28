package datastructures

type QuadTreeNode struct {
	Val bool
	IsLeaf bool
	TopLeft *QuadTreeNode
	TopRight *QuadTreeNode
	BottomLeft *QuadTreeNode
	BottomRight *QuadTreeNode
}