package findmediansortedarrays

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindMedianSortedArrays(t *testing.T) {
	type input struct {
		nums1 []int
		nums2 []int
	}
	inputs := []input{
		{[]int{1, 3}, []int{2}},
		{[]int{1, 2}, []int{3, 4}},
		{[]int{}, []int{1}},
		{[]int{-10, -9, -8}, []int{1, 2}},
	}

	expectedOutputs := []float64{
		2.00000,
		2.50000,
		1.00000,
		-8.00000,
	}

	f := func(i input) float64 {
		return findMedianSortedArrays(i.nums1, i.nums2)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
