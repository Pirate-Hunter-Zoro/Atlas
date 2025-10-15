package datastructures

type NumArray struct {
    og_array []int
	tree_array []int 
}

func Constructor(nums []int) NumArray {
	sums := make([]int, len(nums))
	for i:=range nums {
		if i == 0 {
			sums[i] = nums[i]
		} else {
			sums[i] = sums[i-1] + nums[i]
		}
	}
    tree_array := make([]int, len(nums))
	for i:=range nums {
		k := i + 1
		l := k & -k // value of least significant bit of k
		s := k - l
		// we want the 1-indexed range sum from s to k inclusive
		tree_array[i] = sums[i]
		if s > 0 {
			tree_array[i] -= sums[s-1]
		}
	}

	return NumArray{
		og_array: nums,
		tree_array: tree_array,
	}
}


func (n *NumArray) Update(index int, val int)  {
	addition := val - n.og_array[index]
	k := index + 1
    for k <= len(n.tree_array) {
		n.tree_array[k-1] += addition
		k += k & -k
	}
}


func (n *NumArray) SumRange(left int, right int) int {
	return n.helperSum(right) - n.helperSum(left-1)
}


func (n *NumArray) helperSum(end int) int {
	// Inclusive end - sum from first element to end - the following bitwise indexing assumes 1-indexing for k
	k := end + 1
	s := 0
	for k >= 1 {
		s += n.tree_array[k-1]
		k -= k & -k
	}
	return s
}