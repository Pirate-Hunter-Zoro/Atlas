package leetcode

import (
	"leet-code/datastructures"
	"leet-code/helpermath"
	"math"
)

/*
You are given n identical eggs and you have access to a building with k floors labeled from 1 to n.

You know that there exists a floor f where 0 <= f <= n such that any egg dropped at a floor higher than f will break, and any egg dropped at or below floor f will not break.

Each move, you may take an unbroken egg and drop it from any floor x (where 1 <= x <= n).
If the egg breaks, you can no longer use it.
However, if the egg does not break, you may reuse it in future moves.

Return the minimum number of moves that you need to determine with certainty what the value of f is.

Inpsiration:
https://brilliant.org/wiki/egg-dropping/
*/
func superEggDrop(n int, k int) int {
    // We need to be able to cover n floors...
	// How many drops will it take to cover k floors with n eggs? Binary search...
	left := 1
	right := k
	chooser := helpermath.NewChooseCalculator()
	for left < right {
		mid := int((left + right) / 2)
		num_floors_covered := 0
		// Calculate the number of floors covered given that we have 'mid' drops and n eggs
		for i:=1; i<=n; i++ {
			// From the article
			num_floors_covered += chooser.Choose(mid, i)
			if num_floors_covered < 0 { // avoid integer overflow
				num_floors_covered = int(math.MaxInt)
				break
			}
		}
		if num_floors_covered < k {
			// Need more drops
			left = mid + 1
		} else if num_floors_covered > k {
			// Try using less drops
			right = mid
		} else {
			return mid
		}
	}

	return left
}

/*
Given an array of integers heights representing the histogram's bar height where the width of each bar is 1, return the area of the largest rectangle in the histogram.
*/
func largestRectangleArea(heights []int) int {
	// Answer the question - at this index, what's the farthest right I can go before I run into someone shorter
	shorter_right := make([]int, len(heights))
	for i:=0; i<len(shorter_right); i++ {
		shorter_right[i] = len(heights)
	}
	right_stack := datastructures.NewStack[int]()
	right_stack.Push(0)
	for i, h := range heights {
		if i == 0 {
			continue
		} else {
			for !right_stack.Empty() && heights[right_stack.Peek()] > h {
				shorter_right[right_stack.Pop()] = i
			}
			right_stack.Push(i)
		}
	}
	// Now same for left
	shorter_left := make([]int, len(heights))
	for i:=0; i<len(shorter_left); i++ {
		shorter_left[i] = -1
	}
	left_stack := datastructures.NewStack[int]()
	left_stack.Push(len(heights)-1)
	for i:=len(heights)-2; i>=0; i-- {
		h := heights[i]
		for !left_stack.Empty() && heights[left_stack.Peek()] > h {
			shorter_left[left_stack.Pop()] = i
		}
		left_stack.Push(i)
	}

	record := 0
	for i, h := range heights {
		record = max(record, h * (shorter_right[i]-shorter_left[i]-1))
	}
	return record
}

/*
Given a rows x cols binary matrix filled with 0's and 1's, find the largest rectangle containing only 1's and return its area.
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
		record = max(record, largestRectangleArea(heights))
	}

    return record
}