package maximumlengthii

/*
You are given an integer array nums and a positive integer k.
A subsequence sub of nums with length x is called valid if it satisfies:

(sub[0] + sub[1]) % k == (sub[1] + sub[2]) % k == ... == (sub[x - 2] + sub[x - 1]) % k.
Return the length of the longest valid subsequence of nums.

Link:
https://leetcode.com/problems/find-the-maximum-length-of-valid-subsequence-ii/?envType=daily-question&envId=2025-07-17
*/
func maximumLengthII(nums []int, k int) int {
	for i := range nums {
		nums[i] = nums[i] % k // Reduce all numbers to modulus k
	}

	record := 0
	// Try all possible mod-pair values, and all possible mod-end values
	for modPair := range k {
		dp := make([]int, k) // dp[modEnd] = length of longest valid subsequence ending with this modEnd value
		for _, mod := range nums {
			prevMod := (modPair - mod + k) % k    // The previous mod value that would yield a valid pair with this mod value
			dp[mod] = max(dp[mod], dp[prevMod]+1) // Either we extend the previous subsequence with this mod value, or we don't
		}
		for _, length := range dp {
			// Update the record with the maximum length of a valid subsequence found so far
			record = max(record, length)
		}
	}

	return record
}
