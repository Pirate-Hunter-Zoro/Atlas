package numtrees

/*
Given an integer n, return the number of structurally unique BST's (binary search trees) which has exactly n nodes of unique values from 1 to n.

Link:
https://leetcode.com/problems/unique-binary-search-trees/description/
*/
func numTrees(n int) int {
    sols := make(map[int]int)
	var solve func(i int) int;
	solve = func(n int) int {
		if _, ok := sols[n]; !ok {
			// Need to solve
			switch n {
				case 1:
					sols[n] = 1
				case 2:
					sols[n] = 2
				default:
					sols[n] = 2*solve(n-1)
					for i:=2; i<n; i++ {
						sols[n] += solve(i-1)*solve(n-i)
					}
			}
		}
		return sols[n]
	}
	return solve(n)
}