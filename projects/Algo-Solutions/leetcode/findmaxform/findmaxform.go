package findmaxform

/*
You are given an array of binary strings strs and two integers m and n.

Return the size of the largest subset of strs such that there are at most m 0's and n 1's in the subset.

A set x is a subset of a set y if all elements of x are also elements of y.

Link:
https://leetcode.com/problems/ones-and-zeroes/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func findMaxForm(strs []string, m int, n int) int {
	// We need to find the number of 0's and 1's in each string
	counts := make([][]int, len(strs))
	for i := range strs {
		counts[i] = make([]int, 2)
		for j := range strs[i] {
			if strs[i][j] == '0' {
				counts[i][0]++
			} else {
				counts[i][1]++
			}
		}
	}

	// Now we'll write a top-down helper method
	sols := make([][][]int, len(strs))
	for i := range len(strs) {
		sols[i] = make([][]int, m+1)
		for j := range m + 1 {
			sols[i][j] = make([]int, n+1)
			for k := range n + 1 {
				sols[i][j][k] = -1
			}
		}
	}
	// With dp[i][j][k], we will answer the question - if we are allowed to use up to strings 0-i, j 0's and k 1's left, what is the greatest size subset we can achieve?
	return topDownFindMaxForm(strs, counts, len(strs)-1, m, n, sols)
}

func topDownFindMaxForm(strs []string, counts [][]int, i int, m int, n int, sols [][][]int) int {
	if sols[i][m][n] == -1 {
		// Need to solve this problem
		if i == 0 { // We can only use the first string
			if counts[i][0] <= m && counts[i][1] <= n {
				sols[i][m][n] = 1 // We can fit the string in a subset
			} else {
				sols[i][m][n] = 0 // We cannot fit the string in a subset
			}
		} else {
			// Multiple strings to work with - try including the latest string or not including it
			notInclude := topDownFindMaxForm(strs, counts, i-1, m, n, sols)
			include := 0
			// Check if we can include the latest string
			if counts[i][0] <= m && counts[i][1] <= n {
				newM := m - counts[i][0]
				newN := n - counts[i][1]
				include = 1 + topDownFindMaxForm(strs, counts, i-1, newM, newN, sols)
			}
			// Take the maximum of the two options
			sols[i][m][n] = max(notInclude, include)
		}
	}
	return sols[i][m][n]
}
