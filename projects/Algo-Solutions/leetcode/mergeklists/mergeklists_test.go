package mergeklists

import (
	"algo-solutions/datastructures"
	"algo-solutions/testutil"
	"testing"
)

func TestMergeKLists(t *testing.T) {
	type input struct {
		lists []*datastructures.ListNode
	}
	inputs := []input{
		{
			[]*datastructures.ListNode{
				datastructures.NewListNode([]int{1, 4, 5}),
				datastructures.NewListNode([]int{1, 3, 4}),
				datastructures.NewListNode([]int{2, 6}),
			},
		},
		{
			[]*datastructures.ListNode{},
		},
		{
			[]*datastructures.ListNode{
				datastructures.NewListNode([]int{}),
			},
		},
	}

	expectedOutputs := []*datastructures.ListNode{
		datastructures.NewListNode([]int{1, 1, 2, 3, 4, 4, 5, 6}),
		nil,
		nil,
	}

	f := func(i input) *datastructures.ListNode {
		return mergeKLists(i.lists)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
