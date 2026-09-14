package maxcoins

/*
You are given n balloons, indexed from 0 to n - 1.
Each balloon is painted with a number on it represented by an array nums.
You are asked to burst all the balloons.

If you burst the ith balloon, you will get nums[i - 1] * nums[i] * nums[i + 1] coins.
If i - 1 or i + 1 goes out of bounds of the array, then treat it as if there is a balloon with a 1 painted on it.

Return the maximum coins you can collect by bursting the balloons wisely.

Link:
https://leetcode.com/problems/burst-balloons/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func maxCoins(nums []int) int {
	// Add a 1 to the start and end of the array
	nums = append([]int{1}, nums...)
	nums = append(nums, 1)
	n := len(nums)
	// For a given range, as well as the value of the coin on the left and right, what's the best value we can achieve?
	sols := make([][]int, n)
	for i := range n {
		sols[i] = make([]int, n)
		for j := range n {
			sols[i][j] = -1
		}
	}

	return recMaxCoins(nums, 0, n-1, sols)
}

func recMaxCoins(nums []int, left int, right int, sols [][]int) int {
	if sols[left][right] == -1 {
		// Need to solve this problem - pop everything in between and see what we can get
		if left+1 == right {
			// Base case - no balloons in between to pop
			sols[left][right] = 0
		} else {
			// We do have balloons in between to pop - see which one should be the last to pop
			for last := left + 1; last < right; last++ {
				popLast := nums[left] * nums[last] * nums[right]
				bestLeft := recMaxCoins(nums, left, last, sols)
				bestRight := recMaxCoins(nums, last, right, sols)
				sols[left][right] = max(sols[left][right], popLast+bestLeft+bestRight)
			}
		}
	}
	return sols[left][right]
}
