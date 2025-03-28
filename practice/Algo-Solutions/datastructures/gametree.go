package datastructures

type GameTreeNode struct {
	xPlayer bool
	pos int
	moves []*GameTreeNode
}
func NewGameTreeNode(xPlayer bool, pos int) *GameTreeNode {
	return &GameTreeNode{xPlayer:xPlayer, pos:pos, moves:make([]*GameTreeNode, 9)}
}

type GameTree struct {
	root *GameTreeNode
}
func NewGameTree() *GameTree {
	return &GameTree{root: NewGameTreeNode(false, -1)}
}