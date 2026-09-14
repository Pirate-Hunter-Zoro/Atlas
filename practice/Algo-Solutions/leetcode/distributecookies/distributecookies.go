package distributecookies

import "math"

/*
You are given an integer array cookies, where cookies[i] denotes the number of cookies in the ith bag.
You are also given an integer k that denotes the number of children to distribute all the bags of cookies to.
All the cookies in the same bag must go to the same child and cannot be split up.

The unfairness of a distribution is defined as the maximum total cookies obtained by a single child in the distribution.

Return the minimum unfairness of all distributions.

Link:
https://leetcode.com/problems/fair-distribution-of-cookies/description/
*/
func distributeCookies(cookies []int, k int) int {
	cookieTotals := make([]int, k)
	nextToAssign := 0
	return recDistributeCookies(&cookies, &cookieTotals, nextToAssign)
}

func recDistributeCookies(cookies *[]int, cookieTotals *[]int, nextToAssign int) int {
	// If I’ve assigned the first i cookies, and the kids currently have these totals, what’s the best possible unfairness I can achieve from here?”
	// Each recursive step adds a cookie to a kid and asks the question again.
	cookie := (*cookies)[nextToAssign]
	// Try giving the cookie to each kid
	previousSums := make(map[int]bool)
	record := math.MaxInt
	for i := range *cookieTotals {
		kidSum := (*cookieTotals)[i]
		if _, ok := previousSums[kidSum]; !ok {
			// Not redundant to assign this cookie to this kid
			previousSums[kidSum] = true
			(*cookieTotals)[i] += cookie
			if nextToAssign < len(*cookies)-1 {
				// Follow this branch
				recUnfair := recDistributeCookies(cookies, cookieTotals, nextToAssign+1)
				record = min(record, recUnfair)
			} else {
				// We're at the end of our cookie assignments - check the unfairness
				maxCookieCount := math.MinInt
				for j := range *cookieTotals {
					maxCookieCount = max(maxCookieCount, (*cookieTotals)[j])
				}
				record = min(record, maxCookieCount)
			}
			// Now remove this cookie now that we've left the recursive branch
			(*cookieTotals)[i] -= cookie
		}
	}
	return record
}
