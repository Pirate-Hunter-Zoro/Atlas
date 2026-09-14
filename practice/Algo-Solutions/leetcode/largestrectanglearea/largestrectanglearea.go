package largestrectanglearea

import "algo-solutions/datastructures"

/*
Given an array of integers heights representing the histogram's bar height where the width of each bar is 1, return the area of the largest rectangle in the histogram.

Link: https://leetcode.com/problems/largest-rectangle-in-histogram/
*/
func LargestRectangleArea(heights []int) int {
	// Answer the question - at this index, what's the farthest right I can go before I run into someone shorter
	shorterRight := make([]int, len(heights))
	for i := range shorterRight {
		shorterRight[i] = len(heights)
	}
	rightStack := datastructures.NewStack[int]()
	rightStack.Push(0)
	for i, h := range heights {
		if i == 0 {
			continue
		} else {
			for !rightStack.Empty() && heights[rightStack.Peek()] > h {
				shorterRight[rightStack.Pop()] = i
			}
			rightStack.Push(i)
		}
	}
	// Now same for left
	shorterLeft := make([]int, len(heights))
	for i := range shorterLeft {
		shorterLeft[i] = -1
	}
	leftStack := datastructures.NewStack[int]()
	leftStack.Push(len(heights) - 1)
	for i := len(heights) - 2; i >= 0; i-- {
		h := heights[i]
		for !leftStack.Empty() && heights[leftStack.Peek()] > h {
			shorterLeft[leftStack.Pop()] = i
		}
		leftStack.Push(i)
	}

	record := 0
	for i, h := range heights {
		record = max(record, h*(shorterRight[i]-shorterLeft[i]-1))
	}
	return record
}
