package maxprofitii

/*
You are given an array prices where prices[i] is the price of a given stock on the ith day.

Find the maximum profit you can achieve.
You may complete at most two transactions.

Note: You may not engage in multiple transactions simultaneously (i.e., you must sell the stock before you buy again).

Link:
https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/description/
*/
func maxProfitII(prices []int) int {
	// Consider, on this day, the maximum profit you can achieve given you have:
	// Bought no times
	// Bought once (and must sell before buying again)
	// Bought and sold once
	// Bought and sold once, then bought again
	// Bought and sold twice
	sols := make([][]int, 5)
	for i := range sols {
		sols[i] = make([]int, len(prices))
	}
	for i := range sols {
		for j := range prices {
			sols[i][j] = -1
			if j == len(prices)-1 {
				// Base cases
				sols[0][j] = 0         // Never bought in the past so cannot sell
				sols[1][j] = prices[j] // Bought once, can sell on last day
				sols[2][j] = 0         // Bought once and sold once, must buy again before selling and since we are on the last day, bad idea
				sols[3][j] = prices[j] // Again, can sell on last day
				sols[4][j] = 0         // Nothing left that can be done
			}
		}
	}

	// Now solve the problem
	var f func(day int, bought int) int
	f = func(day int, bought int) int {
		if sols[bought][day] == -1 {
			// Need to solve this problem
			switch bought {
			case 0, 2: // Must buy before selling again
				buy := f(day+1, bought+1) - prices[day]
				noBuy := f(day+1, bought)
				sols[bought][day] = max(buy, noBuy)
			case 1, 3: // Have ability to sell
				// Try selling
				sell := prices[day] + f(day+1, bought+1)
				noSell := f(day+1, bought)
				sols[bought][day] = max(sell, noSell)
			default: // Nothing left that can be done
				sols[bought][day] = 0
			}
		}
		return sols[bought][day]
	}

	return f(0, 0)
}
