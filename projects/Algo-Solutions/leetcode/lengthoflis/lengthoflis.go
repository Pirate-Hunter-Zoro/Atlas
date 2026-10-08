package lengthoflis

/*
Given an integer array nums, return the length of the longest strictly increasing subsequence.

Link:
https://leetcode.com/problems/longest-increasing-subsequence/description/
*/
func lengthOfLIS(nums []int) int {
	length := make([]int, len(nums))
	for i := range nums {
		length[i] = 1
		for j := range i {
			if nums[i] > nums[j] {
				length[i] = max(length[i], length[j]+1)
			}
		}
	}

	record := 1
	for i := range length {
		record = max(record, length[i])
	}
	return record
}

// Now let's do that in O(nlog(n))
func lengthOfLISFast(nums []int) int {
	// Store the smallest tail of all increasing subsequences of the given length
	// e.g. tails[3] signifies the smallest tail of all increasing subsequences of length 3, at the END of our algorithm
	tails := []int{}

	for i := range nums {
		n := nums[i]
		// See if it can extend the longest increasing sequence
		if len(tails) == 0 || tails[len(tails)-1] < n {
			tails = append(tails, n)
		} else {
			// Nums could serve as a smaller last value for an already existing increasing subsequence
			left := 0
			right := len(tails)
			var mid int
			for left < right {
				// Binary search for the first value greater than or equal to n
				mid := int((left + right) / 2)
				if tails[mid] > n {
					// Look left
					right = mid
				} else if tails[mid] < n {
					// Look right
					left = mid + 1
				} else {
					// We found a pre-existing increasing subsequence that ends with n, so we can't do any better
					break
				}
			}
			mid = int((left + right) / 2)
			if tails[mid] > n {
				tails[mid] = n
			}
		}
	}

	return len(tails)
}
