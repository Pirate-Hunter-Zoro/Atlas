package mergeklists

import "algo-solutions/datastructures"

/*
You are given an array of k linked-lists lists, each linked-list is sorted in ascending order.

Merge all the linked-lists into one sorted linked-list and return it.

Link: https://leetcode.com/problems/merge-k-sorted-lists/
*/
func mergeKLists(lists []*datastructures.ListNode) *datastructures.ListNode {
	// Check for edge cases
	nonNull := []*datastructures.ListNode{}
	for _, n := range lists {
		if n != nil {
			nonNull = append(nonNull, n)
		}
	}
	if len(nonNull) == 0 {
		return nil
	}

	// Now we solve the problem with a heap of list nodes going by their first values
	f := func(n1 *datastructures.ListNode, n2 *datastructures.ListNode) bool {
		return n1.Val <= n2.Val
	}
	nodeHeap := datastructures.NewHeap(f)
	for _, n := range nonNull {
		nodeHeap.Push(n)
	}

	// Set up our result to return
	res := &datastructures.ListNode{
		Val:  nodeHeap.Peek().Val,
		Next: nil,
	}
	pop := nodeHeap.Pop()
	if pop.Next != nil {
		nodeHeap.Push(pop.Next)
	}
	pop.Next = nil // not strictly necessary but for the sake of organization
	curr := res
	for !nodeHeap.Empty() {
		pop := nodeHeap.Pop()
		if pop.Next != nil {
			nodeHeap.Push(pop.Next)
		}
		pop.Next = nil
		curr.Next = pop
		curr = curr.Next
	}

	return res
}
