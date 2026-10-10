package coinchange

import (
	"math"
	"sort"
)

/*
You are given an integer array coins representing coins of different denominations and an integer amount representing a total amount of money.

Return the fewest number of coins that you need to make up that amount.
If that amount of money cannot be made up by any combination of the coins, return -1.

You may assume that you have an infinite number of each kind of coin.

Link:
https://leetcode.com/problems/coin-change/description/
*/
func coinChange(coins []int, amount int) int {
	sols := make([]int, amount+1)
	sort.SliceStable(coins, func(i, j int) bool {
		return coins[i] < coins[j]
	})
	for i := 1; i < len(sols); i++ {
		sols[i] = -1 // By default
	}
	// For each amount, try picking every possible coin
	for i := range amount + 1 {
		if i > 0 {
			record := math.MaxInt32
			for j := range coins {
				coin := coins[j]
				left := i - coin
				if left >= 0 && sols[left] != -1 {
					record = min(record, sols[left]+1)
				}
			}
			if record != math.MaxInt32 {
				sols[i] = record
			}
		}
	}

	return sols[amount]
}
