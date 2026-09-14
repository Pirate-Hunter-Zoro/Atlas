package maxprofitiv

/*
You are given an integer array prices where prices[i] is the price of a given stock on the ith day, and an integer k.
Find the maximum profit you can achieve.
You may complete at most k transactions: i.e. you may buy at most k times and sell at most k times.

Note: You may not engage in multiple transactions simultaneously (i.e., you must sell the stock before you buy again).

Link:
https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iv/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func maxProfitIV(k int, prices []int) int {
	// We need to answer two questions
	solsSell := make([][]int, k+1) // On a given day, given we have k transactions left, how much profit can we make given we need to sell?
	solsBuy := make([][]int, k+1)  // On a given day, given we have k transactions left, how much profit can we make given we can only buy?
	for j := range k + 1 {
		solsSell[j] = make([]int, len(prices))
		solsBuy[j] = make([]int, len(prices))
	}
	for day := len(prices) - 1; day >= 0; day-- {
		if day == len(prices)-1 {
			// Base case - last day - if we can sell the best thing to do is sell
			for i := range k + 1 {
				solsSell[i][day] = prices[day]
			}
			// If we cannot sell, certainly don't buy on the last day
		} else {
			for i := range k + 1 {
				if i == 0 {
					// We can't buy anymore but selling could get us something
					// Try selling either today, or the best later time to sell
					solsSell[i][day] = max(prices[day], solsSell[i][day+1])
				} else {
					// We have at least one transaction left
					// In the case of having nothing to sell, try buying or not buying
					solsBuy[i][day] = max(solsBuy[i][day+1], solsSell[i][day+1]-prices[day])
					// In the case of having something to sell, try selling now or later
					// Whenever we sell, we must decrease the number of transactions left
					solsSell[i][day] = max(solsSell[i][day+1], prices[day]+solsBuy[i-1][day+1])
				}
			}
		}
	}

	return solsBuy[k][0]
}
