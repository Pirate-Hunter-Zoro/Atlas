package maximumlength

/*
You are given an integer array nums.
A subsequence sub of nums with length x is called valid if it satisfies:

(sub[0] + sub[1]) % 2 == (sub[1] + sub[2]) % 2 == ... == (sub[x - 2] + sub[x - 1]) % 2.
Return the length of the longest valid subsequence of nums.

A subsequence is an array that can be derived from another array by deleting some or no elements without changing the order of the remaining elements.

Link:
https://leetcode.com/problems/find-the-maximum-length-of-valid-subsequence-i/description/
*/
func maximumLength(nums []int) int {
	for i := range nums {
		nums[i] = nums[i] % 2 // Reduce all numbers to 0 or 1
	}
	// Answer the question, with this pair modulus value and a last value with this modulus value, ending at or before this index, what is the longest valid subsequence achievable?
	sols := make([][][]int, 2)
	for i := range 2 {
		sols[i] = make([][]int, 2)
		for j := range 2 {
			sols[i][j] = make([]int, len(nums)) // Initialize the subsequence lengths to 0
		}
	}
	for i := range len(nums) {
		if i == 0 {
			sols[1][nums[i]][i] = 1 // The first element can only yield a subsequence of length 1 - possible mod values determined by future subsequence elements
			sols[0][nums[i]][i] = 1
		} else {
			// Try excluding this element
			sols[0][0][i] = sols[0][0][i-1] // Carry over the previous subsequence length
			sols[0][1][i] = sols[0][1][i-1]
			sols[1][0][i] = sols[1][0][i-1]
			sols[1][1][i] = sols[1][1][i-1]
			// Try including this element in the subsequence
			// If this element's modulus is 1, then to achieve a 0 mod pair, the previous element must have been 1 coming from a 0 mod pair subsequence
			if nums[i] == 1 {
				// 0 modulus pair, 1 modulus end, so we can extend the previous 0 modulus pair 1 modulus end subsequence (and you might as well add an element when you can)
				sols[0][1][i] += 1
				// 1 modulus pair, 1 modulus end, so we can extend the previous 1 modulus pair 0 modulus end subsequence if it benefits us
				sols[1][1][i] = max(sols[1][1][i], sols[1][0][i-1]+1)
			} else {
				// 0 modulus pair, 0 modulus end, so we can extend the previous 0 modulus pair 0 modulus end subsequence (and you might as well add an element when you can)
				sols[0][0][i] += 1
				// 1 modulus pair, 0 modulus end, so we can extend the previous 1 modulus pair 1 modulus end subsequence if it benefits us
				sols[1][0][i] = max(sols[1][0][i], sols[1][1][i-1]+1)
			}
		}

	}

	return max(sols[0][0][len(nums)-1], max(sols[0][1][len(nums)-1], max(sols[1][0][len(nums)-1], sols[1][1][len(nums)-1])))
}
