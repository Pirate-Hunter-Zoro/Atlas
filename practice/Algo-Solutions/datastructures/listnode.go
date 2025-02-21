package datastructures

type ListNode struct {
	Val int
	Next *ListNode
}
func NewListNode(values []int) *ListNode {
	if len(values) == 0 {
		return nil
	} else {
		root := &ListNode{
			Val: values[0],
		}
		curr := root
		for i:=1; i<len(values); i++ {
			curr.Next = &ListNode{
				Val: values[i],
			}
			curr = curr.Next
		}
		return root
	}
}
func ListNodeEquals(first *ListNode, second *ListNode) bool {
	if first == nil {
		return second == nil
	} else if second == nil {
		return false
	} else if first.Val != second.Val {
		return false
	} else {
		return ListNodeEquals(first.Next, second.Next)
	}
}