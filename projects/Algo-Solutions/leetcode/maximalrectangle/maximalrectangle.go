package maximalrectangle

import "algo-solutions/leetcode/largestrectanglearea"

/*
Given a rows x cols binary matrix filled with 0's and 1's, find the largest rectangle containing only 1's and return its area.

Link: https://leetcode.com/problems/maximal-rectangle/
*/
func maximalRectangle(matrix [][]byte) int {
	// Keep a running histogram going
	heights := make([]int, len(matrix[0]))
	record := 0
	for _, row := range matrix {
		for i, c := range row {
			if c == '1' {
				heights[i] += 1
			} else {
				heights[i] = 0
			}
		}
		record = max(record, largestrectanglearea.LargestRectangleArea(heights))
	}

	return record
}
