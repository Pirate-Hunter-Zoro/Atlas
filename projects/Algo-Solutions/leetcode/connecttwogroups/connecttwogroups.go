package connecttwogroups

import "math"

/*
You are given two groups of points where the first group has size1 points, the second group has size2 points, and size1 >= size2.

The cost of the connection between any two points are given in an size1 x size2 matrix where cost[i][j] is the cost of connecting point i of the first group and point j of the second group.
The groups are connected if each point in both groups is connected to one or more points in the opposite group.
In other words, each point in the first group must be connected to at least one point in the second group, and each point in the second group must be connected to at least one point in the first group.

Return the minimum cost it takes to connect the two groups.

Link:
https://leetcode.com/problems/minimum-cost-to-connect-two-groups-of-points/description/
Inspiration: https://leetcode.com/problems/minimum-cost-to-connect-two-groups-of-points/solutions/5854369/beats-100-on-runtime-and-memory-explained/
*/
func connectTwoGroups(cost [][]int) int {
	// First find the minimum cost for each node in the right to connect to any node in the left
	nLeft := len(cost)
	nRight := len(cost[0])
	minCostConnect := make([]int, nRight)
	for i := range nRight {
		minCostConnect[i] = math.MaxInt
		for j := range nLeft {
			minCostConnect[i] = min(minCostConnect[i], cost[j][i])
		}
	}

	// Now we are ready to answer the question, given left nodes 1 through 'k' have been connected, and bit mask 'b' of the right nodes have been connected, what is the minimum cost to complete our connections?
	sols := make([][]int, nLeft+1)
	for i := range nLeft + 1 {
		sols[i] = make([]int, 1<<nRight)
		for j := range 1 << nRight {
			sols[i][j] = -1
		}
	}
	return recMinConnectTwoGroups(0, 0, sols, minCostConnect, cost, nLeft, nRight)
}

func recMinConnectTwoGroups(numLeftConnected int, bitMaskRight int, sols [][]int, minCostConnect []int, cost [][]int, nLeft int, nRight int) int {
	if sols[numLeftConnected][bitMaskRight] == -1 {
		// Need to solve this problem
		if numLeftConnected == nLeft {
			// Base case - all the left nodes are connected, so see which right nodes still need to be connected and connect each with their min cost
			totalCost := 0
			for i := range nRight {
				if (1<<i)&bitMaskRight == 0 {
					// Node i on the right needs to be connected
					totalCost += minCostConnect[i]
				}
			}
			sols[numLeftConnected][bitMaskRight] = totalCost
		} else {
			// Try connecting the next left node with any node in the right
			totalCost := math.MaxInt
			for i := range nRight {
				// Try connecting the next left node with Node i on the right
				newBitMask := bitMaskRight | (1 << i)
				totalCost = min(totalCost, cost[numLeftConnected][i]+recMinConnectTwoGroups(numLeftConnected+1, newBitMask, sols, minCostConnect, cost, nLeft, nRight))
			}
			sols[numLeftConnected][bitMaskRight] = totalCost
		}
	}
	return sols[numLeftConnected][bitMaskRight]
}
