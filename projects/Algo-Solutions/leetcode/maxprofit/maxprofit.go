package maxprofit

import "math"

/*
You are given an integer n, representing the number of employees in a company.
Each employee is assigned a unique ID from 1 to n, and employee 1 is the CEO.
You are given two 1-based integer arrays, present and future, each of length n, where:
  - present[i] represents the current price at which the ith employee can buy a stock today.
  - future[i] represents the expected price at which the ith employee can sell the stock tomorrow.

The company's hierarchy is represented by a 2D integer array hierarchy, where hierarchy[i] = [uᵢ, vᵢ] means that employee uᵢ is the direct boss of employee vᵢ.

Additionally, you have an integer budget representing the total funds available for investment.

However, the company has a discount policy: if an employee's direct boss purchases their own stock, then the employee can buy their stock at half the original price (floor(present[v] / 2)).

Return the maximum profit that can be achieved without exceeding the given budget.

Note:
  - You may buy each stock at most once.
  - You cannot use any profit earned from future stock prices to fund additional investments and must buy only from budget.

Link:
https://leetcode.com/problems/maximum-profit-from-trading-stocks-with-discounts/description/?envType=daily-question&envId=2025-12-16
*/
func maxProfit(n int, present []int, future []int, hierarchy [][]int, budget int) int {
	// First we need to create a tree out of the hierarchy - essentially, if uI is the direct boss if vI, then vI must buy after uI when we consider the problem
	type node struct {
		id       int
		children []*node
	}
	allNodes := make([]*node, n)
	for i := range n {
		allNodes[i] = &node{
			i + 1,
			[]*node{},
		}
	}

	for _, r := range hierarchy {
		u := r[0]
		v := r[1]
		// Now we need to modify our graph
		allNodes[u-1].children = append(allNodes[u-1].children, allNodes[v-1])
	}

	// Using dynamic programming, we must keep track of our state, including the current index, the remaining budget, and if the parent has bought yet
	dp := make([][][]int, 2)
	dp[0] = make([][]int, n)
	dp[1] = make([][]int, n)
	for i := range n {
		dp[0][i] = make([]int, budget+1)
		dp[1][i] = make([]int, budget+1)
		for j := range budget + 1 {
			dp[0][i][j] = -1
			dp[1][i][j] = -1
		}
	}
	// dp[0][u][b] is the maximum profit achievable for the subtree from u down with budget b and with the parent NOT having bought the stock
	// dp[1][u][b] is the same with the parent of u HAVING bought the stock
	var solve func(id int, parentBought int) []int
	solve = func(id int, parentBought int) []int {
		if dp[parentBought][id-1][budget] == -1 {
			// Need to solve this problem

			// For this node (employee), we need to know the best profits possible over all possible budgets allocated to all children if we do NOT buy
			profitsNoBuy := make([]int, budget+1)
			// Start with children
			for _, n := range allNodes[id-1].children {
				// What is the profit I can get out of this child if I give them all possible budgets from 0 to budget?
				childProfits := solve(n.id, 0)
				for j := budget; j >= 0; j-- {
					// I have j budget to split between this child and ALL PREVIOUS children
					for k := 0; k <= j; k++ {
						// Give k to this specific child and see what profit is achieved - profitsBuy[j-k] is whatever can be done with all other children
						profitsNoBuy[j] = max(profitsNoBuy[j], childProfits[k]+profitsNoBuy[j-k])
					}
				}
			}

			// Same, but now if we do buy (but don't worry about the fact that this changes the budget available - that logic comes below)
			profitsBuy := make([]int, budget+1)
			for _, n := range allNodes[id-1].children {
				childProfits := solve(n.id, 1)
				for j := budget; j >= 0; j-- {
					for k := 0; k <= j; k++ {
						// Give the current child (supervisee) this much money to work with and leave j-k for every other child already processed
						profitsBuy[j] = max(profitsBuy[j], childProfits[k]+profitsBuy[j-k]) // Leaves j-k for the rest of the children to work with
					}
				}
			}

			// Now we fill out the total dp array
			cost := present[id-1]
			if parentBought == 1 {
				// Divide cost by 2
				cost = int(math.Floor(float64(cost) / 2))
			}
			immediateProfit := future[id-1] - cost
			for j := range budget + 1 {
				dp[parentBought][id-1][j] = profitsNoBuy[j]
				if cost <= j {
					// Buying is an option - consider it
					dp[parentBought][id-1][j] = max(dp[parentBought][id-1][j], immediateProfit+profitsBuy[j-cost])
				}
			}

		}
		return dp[parentBought][id-1]
	}

	// The CEO does not have a parent (direct supervisor) who can buy
	return solve(1, 0)[budget]
}
