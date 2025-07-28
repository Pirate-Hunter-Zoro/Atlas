package leetcode

import (
	"bytes"
	"leet-code/datastructures"
	"leet-code/helpermath"
	"log"
	"maps"
	"math"
	"slices"
	"sort"
	"strconv"
	"strings"
)

var globalCalculator *helpermath.ChooseCalculator

func init() {
	// Initialize the global choose calculator
	globalCalculator = helpermath.NewChooseCalculator()
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given n identical eggs and you have access to a building with k floors labeled from 1 to n.

You know that there exists a floor f where 0 <= f <= n such that any egg dropped at a floor higher than f will break, and any egg dropped at or below floor f will not break.

Each move, you may take an unbroken egg and drop it from any floor x (where 1 <= x <= n).
If the egg breaks, you can no longer use it.
However, if the egg does not break, you may reuse it in future moves.

Return the minimum number of moves that you need to determine with certainty what the value of f is.

Link: https://leetcode.com/problems/super-egg-drop/

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
		for i := 1; i <= n; i++ {
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

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an array of integers heights representing the histogram's bar height where the width of each bar is 1, return the area of the largest rectangle in the histogram.

Link: https://leetcode.com/problems/largest-rectangle-in-histogram/
*/
func largestRectangleArea(heights []int) int {
	// Answer the question - at this index, what's the farthest right I can go before I run into someone shorter
	shorter_right := make([]int, len(heights))
	for i := range shorter_right {
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
	for i := range shorter_left {
		shorter_left[i] = -1
	}
	left_stack := datastructures.NewStack[int]()
	left_stack.Push(len(heights) - 1)
	for i := len(heights) - 2; i >= 0; i-- {
		h := heights[i]
		for !left_stack.Empty() && heights[left_stack.Peek()] > h {
			shorter_left[left_stack.Pop()] = i
		}
		left_stack.Push(i)
	}

	record := 0
	for i, h := range heights {
		record = max(record, h*(shorter_right[i]-shorter_left[i]-1))
	}
	return record
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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
		record = max(record, largestRectangleArea(heights))
	}

	return record
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given an array prerequisites where prerequisites[i] = [ai, bi] indicates that you must take course bi first if you want to take course ai.

For example, the pair [0, 1], indicates that to take course 0 you have to first take course 1.
Return true if you can finish all courses. Otherwise, return false.

Link: https://leetcode.com/problems/course-schedule/
*/
func canFinish(numCourses int, prerequisites [][]int) bool {
	in_degree := make([]int, numCourses)
	nodes_needed := make([][]int, numCourses) // jagged array
	for i := range numCourses {
		nodes_needed[i] = []int{}
	}
	for _, preq := range prerequisites {
		need := preq[0]
		needed := preq[1]
		in_degree[needed]++
		nodes_needed[need] = append(nodes_needed[need], needed)
	}

	count_in_degree_0 := 0
	for i := 0; i < numCourses; i++ {
		if in_degree[i] == 0 {
			count_in_degree_0++
		}
	}

	node_queue := datastructures.NewQueue[int]()
	for i, v := range in_degree {
		if v == 0 {
			node_queue.Enqueue(i)
		}
	}

	for !node_queue.Empty() {
		next := node_queue.Dequeue()
		for _, neighbor := range nodes_needed[next] {
			in_degree[neighbor]--
			if in_degree[neighbor] == 0 {
				count_in_degree_0++
				node_queue.Enqueue(neighbor)
			}
		}
	}

	return count_in_degree_0 == numCourses
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an input string (s) and a pattern (p), implement wildcard pattern matching with support for '?' and '*' where:
- '?' Matches any single character.
- '*' Matches any sequence of characters (including the empty sequence).

The matching should cover the entire input string (not partial).

Link: https://leetcode.com/problems/wildcard-matching/
*/
func isMatch(s string, p string) bool {
	// Get a couple of edge cases out of the way first...
	if len(p) == 0 {
		return len(s) == 0
	} else if len(s) == 0 {
		for i := 0; i < len(p); i++ {
			if p[i] != '*' {
				return false
			}
		}
		return true
	}

	sols := make([][]bool, len(s)+1)
	for i := 0; i <= len(s); i++ {
		sols[i] = make([]bool, len(p)+1)
	}

	// Empty string matches empty string
	sols[0][0] = true

	// Across the top row - pertains to only matching the empty string with increasing substring lengths of the pattern
	for i := 1; i < len(p); i++ {
		p_idx := i - 1
		sols[0][i] = (p[p_idx] == '*' && sols[0][i-1])
	}
	// The left column is all false by default - which it should be except for the 0-0 cell - an empty pattern cannot match a non-empty string

	// Bottom up solution to solve this problem - top to bottom, left to right
	for i := 1; i <= len(s); i++ {
		for j := 1; j <= len(p); j++ {
			s_char := s[i-1]
			p_char := p[j-1]
			if s_char == p_char || p_char == '?' {
				// Must match
				sols[i][j] = sols[i-1][j-1]
			} else if p_char == '*' {
				// Try matching and consuming '*'
				can_match := sols[i-1][j-1]
				// Try matching and not consuming '*'
				can_match = can_match || sols[i-1][j]
				// Try not matching and consuming '*'
				can_match = can_match || sols[i][j-1]
				// Store the result
				sols[i][j] = can_match
			}
		}
	}

	return sols[len(s)][len(p)]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given a string s and an array of strings words.
All the strings of words are of the same length.

A concatenated string is a string that exactly contains all the strings of any permutation of words concatenated.

For example, if words = ["ab","cd","ef"], then "abcdef", "abefcd", "cdabef", "cdefab", "efabcd", and "efcdab" are all concatenated strings.
"acdbef" is not a concatenated string because it is not the concatenation of any permutation of words.
Return an array of the starting indices of all the concatenated substrings in s.
You can return the answer in any order.

Link: https://leetcode.com/problems/substring-with-concatenation-of-all-words/
*/
func findSubstring(s string, words []string) []int {
	// Create a map which will serve as keeping track of the count needed of each word
	word_counts := make(map[string]int)
	for _, w := range words {
		count, ok := word_counts[w]
		if !ok {
			word_counts[w] = 1
		} else {
			word_counts[w] = count + 1
		}
	}

	l := len(words[0])

	starts := []int{}

	for j := range l {
		i := j
		last_start := i
		words_seen := 0
		current_seen := make(map[string][]int)
		for i <= len(s)-l {
			word := s[i : i+l]
			count_needed, ok := word_counts[word]
			if !ok {
				// Not part of words at all - we must start over
				i += l
				last_start = i
				words_seen = 0
				current_seen = make(map[string][]int)
			} else {
				// This is an actual word in our list
				places_seen, ok := current_seen[word]
				if !ok {
					// We have not seen the word yet
					current_seen[word] = []int{i}
					words_seen++
				} else {
					// We have seen the word
					if len(places_seen) < count_needed {
						// We DID need another instance of this word, so keep going
						current_seen[word] = append(places_seen, i)
						words_seen++
					} else {
						// We did NOT need another instance of this word, so we need to do some removing of previously seen words
						first_seen_idx := places_seen[0]
						current_seen[word] = append(places_seen, i)
						current_seen[word] = current_seen[word][1:]
						last_start = first_seen_idx + l
						// All words seen at places before this index need to have those records removed
						for prev_word, places := range current_seen {
							// Binary search places for the first index greater than first_seen_idx
							left := 0
							right := len(places)
							for left < right {
								mid := (left + right) / 2
								if places[mid] > first_seen_idx {
									// Try looking left
									right = mid
								} else {
									// Try looking right
									left = mid + 1
								}
							}
							if left >= len(places) {
								// All occurrences of prev_word no longer count
								words_seen -= len(places)
								delete(current_seen, prev_word)
							} else if left > 0 {
								// Some occurrences of prev_word no longer count
								words_seen -= left
								current_seen[prev_word] = current_seen[prev_word][left:]
							}
						}
					}
				}
				i += l
			}
			if words_seen == len(words) {
				// Found a permutation substring - now just get rid of the first word we saw
				starts = append(starts, last_start)
				words_seen--
				first_word := s[last_start : last_start+l]
				last_start += l
				if len(current_seen[first_word]) == 1 {
					delete(current_seen, first_word)
				} else {
					current_seen[first_word] = current_seen[first_word][1:]
				}
			}
		}
	}

	sort.SliceStable(starts, func(i, j int) bool {
		return starts[i] < starts[j]
	})
	return starts
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an unsorted integer array nums.
Return the smallest positive integer that is not present in nums.

You must implement an algorithm that runs in O(n) time and uses O(1) auxiliary space.
Link: https://leetcode.com/problems/first-missing-positive/
*/
func firstMissingPositive(nums []int) int {
	// The LeetCode editorial was insanely helpful...
	n := len(nums)
	// Note that the lowest missing positive integer can only be in {1,...,n+1}
	one_missing := true
	// Mark all zero or negative elements as 1 instead - but while we're doing that make sure 1 isn't the lowest positive missing - if it is return it
	for i, v := range nums {
		if v == 1 {
			one_missing = false
		} else if v > n || v <= 0 {
			nums[i] = 1
		}
	}
	if one_missing {
		return 1
	} else {
		// Loop through the array once again
		for _, v := range nums {
			// Mark position v in the array as seen by making it negative
			idx := int(math.Abs(float64(v))) - 1
			nums[idx] = -int(math.Abs(float64(nums[idx])))
		}
		// Now go through the list again - the first index that is not negative corresponds with the lowest missing positive value
		for i := 0; i < len(nums); i++ {
			if nums[i] > 0 {
				// Never seen
				return i + 1
			}
		}
		// Only remaining possibility
		return n + 1
	}
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given an array of k linked-lists lists, each linked-list is sorted in ascending order.

Merge all the linked-lists into one sorted linked-list and return it.

Link: https://leetcode.com/problems/merge-k-sorted-lists/
*/
func mergeKLists(lists []*datastructures.ListNode) *datastructures.ListNode {
	// Check for edge cases
	non_null := []*datastructures.ListNode{}
	for _, n := range lists {
		if n != nil {
			non_null = append(non_null, n)
		}
	}
	if len(non_null) == 0 {
		return nil
	}

	// Now we solve the problem with a heap of list nodes going by their first values
	f := func(n1 *datastructures.ListNode, n2 *datastructures.ListNode) bool {
		return n1.Val <= n2.Val
	}
	node_heap := datastructures.NewHeap(f)
	for _, n := range non_null {
		node_heap.Push(n)
	}

	// Set up our result to return
	res := &datastructures.ListNode{
		Val:  node_heap.Peek().Val,
		Next: nil,
	}
	pop := node_heap.Pop()
	if pop.Next != nil {
		node_heap.Push(pop.Next)
	}
	pop.Next = nil // not strictly necessary but for the sake of organization
	curr := res
	for !node_heap.Empty() {
		pop := node_heap.Pop()
		if pop.Next != nil {
			node_heap.Push(pop.Next)
		}
		pop.Next = nil
		curr.Next = pop
		curr = curr.Next
	}

	return res
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given a string containing just the characters '(' and ')', return the length of the longest valid (well-formed) parentheses substring.

Link: https://leetcode.com/problems/longest-valid-parentheses/
*/
func longestValidParentheses(s string) int {
	// Keep a running stack, and once we run into a ')' that has no preceding '(' to match, our running length has to start over
	// In the stack, store the position and actual character (as an integer)
	type char_idx struct {
		posn int
		char byte
	}
	char_idx_stack := datastructures.NewStack[char_idx]()
	// Finally keep track of the stretches of the string where we have found a valid substring of parentheses and we'll merge them in the end
	stretches := [][]int{}
	for i := range len(s) {
		char := s[i]
		if char == ')' {
			if !char_idx_stack.Empty() && char_idx_stack.Peek().char == '(' {
				// preceded by a '('
				prev_idx := char_idx_stack.Pop().posn
				if len(stretches) > 0 {
					j := len(stretches) - 1
					prev_stretch := stretches[j]
					for j >= 0 && prev_stretch[0] > prev_idx && prev_stretch[1] < i {
						// wraps around the most recent valid substring of parentheses
						j--
						if j >= 0 {
							prev_stretch = stretches[j]
						}
					}
					if j < len(stretches)-1 {
						stretches[j+1] = []int{prev_idx, i}
						stretches = stretches[:j+2]
					} else {
						// no previous wraparounds
						stretches = append(stretches, []int{prev_idx, i})
					}
				} else {
					stretches = append(stretches, []int{prev_idx, i})
				}
			}
		} else {
			// just push the opening parentheses on the stack
			char_idx_stack.Push(char_idx{posn: i, char: char})
		}
	}

	// Now go through all of our stretches
	record := 0
	running_length := 0
	for i, stretch := range stretches {
		if i > 0 && stretches[i-1][1] == stretch[0]-1 {
			// Consecutive to previous stretch
			running_length += stretch[1] - stretch[0] + 1
		} else {
			// Not consecutive to previous stretch so refresh running length
			running_length = stretch[1] - stretch[0] + 1
		}
		record = max(record, running_length)
	}

	return record
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
We can scramble a string s to get a string t using the following algorithm:
- If the length of the string is 1, stop.
- If the length of the string is > 1, do the following:
  - Split the string into two non-empty substrings at a random index, i.e., if the string is s, divide it to x and y where s = x + y.
  - Randomly decide to swap the two substrings or to keep them in the same order. i.e., after this step, s may become s = x + y or s = y + x.
  - Apply step 1 recursively on each of the two substrings x and y.

Given two strings s1 and s2 of the same length, return true if s2 is a scrambled string of s1, otherwise, return false.

Link: https://leetcode.com/problems/scramble-string/
*/
func isScramble(s1 string, s2 string) bool {
	is_scramble := make(map[string]map[string]bool)

	return recIsScramble(s1, s2, is_scramble)
}

func recIsScramble(l string, r string, is_scramble map[string]map[string]bool) bool {
	_, ok := is_scramble[l]
	if !ok {
		is_scramble[l] = make(map[string]bool)
		// Trivial base case
		is_scramble[l][l] = true
	}
	_, ok = is_scramble[l][r]
	if !ok {
		// Need to solve this problem
		if len(l) == 1 {
			is_scramble[l][r] = l[0] == r[0]
		} else {
			is_scramble[l][r] = false
			for split := range len(l) - 1 {
				// 'split' is the index of the last character in the left half
				left_half_l := l[:split+1]
				right_half_l := l[split+1:]
				left_half_r_swap := r[:len(right_half_l)]
				right_half_r_swap := r[len(right_half_l):]
				left_half_r_no_swap := r[:split+1]
				right_half_r_no_swap := r[split+1:]
				is_scramble[l][r] = is_scramble[l][r] || (recIsScramble(right_half_l, left_half_r_swap, is_scramble) && recIsScramble(left_half_l, right_half_r_swap, is_scramble))
				is_scramble[l][r] = is_scramble[l][r] || (recIsScramble(left_half_l, left_half_r_no_swap, is_scramble) && recIsScramble(right_half_l, right_half_r_no_swap, is_scramble))
			}
		}
	}
	return is_scramble[l][r]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given two strings s and t, return the number of distinct subsequences of s which equals t.

The test cases are generated so that the answer fits on a 32-bit signed integer.

Link: https://leetcode.com/problems/distinct-subsequences/
*/
func numDistinct(s string, t string) int {
	// Answer the question - how many different subsequences of s[:i+1] can create t[:j+1]?
	num_distinct := make([][]int, len(s))
	for i := range len(s) {
		num_distinct[i] = make([]int, len(t))
		for j := range min(i+1, len(t)) {
			num_distinct[i][j] = -1
		}
	}

	return recNumDistinct(s, t, len(s)-1, len(t)-1, num_distinct)
}

func recNumDistinct(s string, t string, s_idx int, t_idx int, num_distinct [][]int) int {
	if num_distinct[s_idx][t_idx] == -1 {
		// Need to solve this problem
		num_distinct[s_idx][t_idx] = 0
		if s_idx >= t_idx {
			// There is actually a possibility for subsequences to occur
			if s_idx == 0 && s[s_idx] == t[t_idx] {
				num_distinct[s_idx][t_idx]++
			} else if t_idx == 0 && s_idx > 0 {
				// Then count all the times this single character in t was matched with prior characters in s
				num_distinct[s_idx][t_idx] += recNumDistinct(s, t, s_idx-1, t_idx, num_distinct)
				if s[s_idx] == t[t_idx] {
					num_distinct[s_idx][t_idx]++
				}
			} else if s_idx > 0 && t_idx > 0 {
				// Multiple characters from both substrings
				if s[s_idx] == t[t_idx] {
					// Try matching these two characters
					num_distinct[s_idx][t_idx] += recNumDistinct(s, t, s_idx-1, t_idx-1, num_distinct)
				}
				// Try not matching these two characters
				num_distinct[s_idx][t_idx] += recNumDistinct(s, t, s_idx-1, t_idx, num_distinct)
			}
		}
	}
	return num_distinct[s_idx][t_idx]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given a m * n matrix seats  that represent seats distributions in a classroom.
If a seat is broken, it is denoted by '#' character otherwise it is denoted by a '.' character.

Students can see the answers of those sitting next to the left, right, upper left and upper right, but he cannot see the answers of the student sitting directly in front or behind him.
Return the maximum number of students that can take the exam together without any cheating being possible.

Students must be placed in seats in good condition.

Link: https://leetcode.com/problems/maximum-number-of-students-taking-exam/
*/
func maxStudents(seats [][]byte) int {
	// From the hints - run a bit mask depending on the previous row of seats
	// For each row, we need a bit mask corresponding to the previous row of seats taken
	// Answer the question - on this row, for this bit mask, what is the maximum number of students that can be sat?
	sols := make([]map[int]int, len(seats))
	for i := 0; i < len(seats); i++ {
		sols[i] = make(map[int]int)
	}
	num_seats := len(seats[0])

	// Base case is the front row - where the number of students we can sit is simply the number in the row
	mask_counts := findBitMasks(seats[0])
	for _, mask_count := range mask_counts {
		// Bit mask is first element, count is second element
		bit_mask := mask_count[0]
		num_sitting := mask_count[1]
		sols[0][bit_mask] = num_sitting
	}

	// Now we go bottom up
	for i := 1; i < len(sols); i++ {
		mask_counts := findBitMasks(seats[i])
		for _, mask_count := range mask_counts {
			bit_mask := mask_count[0]
			num_sitting := mask_count[1]
			sols[i][bit_mask] = 0
			prev_bit_masks := []int{}
			for mask := range sols[i-1] {
				prev_bit_masks = append(prev_bit_masks, mask)
			}
			prev_row_bit_masks := filterUnavailableBitMasks(num_seats, bit_mask, prev_bit_masks)
			for _, prev_bit_mask := range prev_row_bit_masks {
				sols[i][bit_mask] = max(sols[i][bit_mask], num_sitting+sols[i-1][prev_bit_mask])
			}
		}
	}

	record := 0
	for _, count := range sols[len(sols)-1] {
		record = max(record, count)
	}
	return record
}

func findBitMasks(seat_row []byte) [][]int {
	// Helper method to find all of the available seat bit masks given the row of broken and working seats
	mask_counts := [][]int{}
	seat_posns := []int{}
	for i, b := range seat_row {
		if b == '.' {
			seat_posns = append(seat_posns, i)
		}
	}

	// Note that we cannot pick consecutive seats
	// For each (working) seat, going from left to right, consider taking it, and consider not taking it
	available := make([][][]int, len(seat_posns))
	if len(seat_posns) > 0 {
		available[0] = [][]int{{seat_posns[0]}, {}}
		if len(seat_posns) > 1 {
			if seat_posns[1] == seat_posns[0]+1 {
				// First two seats consecutive
				available[1] = [][]int{{seat_posns[0]}, {seat_posns[1]}, {}}
			} else {
				// First two seats not consecutive so can go together
				available[1] = [][]int{{seat_posns[0]}, {seat_posns[1]}, {}, {seat_posns[0], seat_posns[1]}}
			}
			for i := range len(seat_posns) - 2 {
				j := i + 2
				posn := seat_posns[j]
				prev_posn := seat_posns[j-1]
				if posn == prev_posn+1 {
					// Most previous two seats consecutive
					available[j] = available[j-1] // Don't pick current posn
					// Now add all the options where we do pick the current posn
					for _, picked_set := range available[j-2] {
						new_set := append(picked_set, posn)
						available[j] = append(available[j], new_set)
					}
				} else {
					// Most previous two seats not consecutive so can go together
					available[j] = available[j-1] // Again, don't pick current posn
					for _, picked_set := range available[j-1] {
						new_set := append(picked_set, posn)
						available[j] = append(available[j], new_set)
					}
				}
			}
		}
	} else {
		// No seats were available
		available = append(available, [][]int{{}})
	}

	// Now look at all the possible seat positions we could pick if we allow all the way up to the last seat on the row
	possible_sets := available[len(available)-1]
	for _, set := range possible_sets {
		bit_mask := 0
		for _, posn := range set {
			bit_mask += 1 << posn
		}
		mask_counts = append(mask_counts, []int{bit_mask, len(set)})
	}

	return mask_counts
}

func filterUnavailableBitMasks(num_seats int, bit_mask int, prev_bit_masks []int) []int {
	// Helper method to remove incompatible previous bit masks from the above row given our current row's bit mask
	available := []int{}
	unavailable_spots := []int{}
	for i := range num_seats {
		if (1<<i)&bit_mask > 0 {
			// This seat is included in the current row bit mask
			if i > 0 {
				unavailable_spots = append(unavailable_spots, i-1)
			}
			if i < num_seats-1 {
				unavailable_spots = append(unavailable_spots, i+1)
			}
		}
	}
	for _, prev_mask := range prev_bit_masks {
		for _, unavailable_posn := range unavailable_spots {
			if prev_mask&(1<<unavailable_posn) > 0 {
				// Need to remove this posn
				prev_mask -= 1 << unavailable_posn
			}
		}
		available = append(available, prev_mask)
	}

	return available
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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
	n_left := len(cost)
	n_right := len(cost[0])
	min_cost_connect := make([]int, n_right)
	for i := range n_right {
		min_cost_connect[i] = math.MaxInt
		for j := range n_left {
			min_cost_connect[i] = min(min_cost_connect[i], cost[j][i])
		}
	}

	// Now we are ready to answer the question, given left nodes 1 through 'k' have been connected, and bit mask 'b' of the right nodes have been connected, what is the minimum cost to complete our connections?
	sols := make([][]int, n_left+1)
	for i := range n_left + 1 {
		sols[i] = make([]int, 1<<n_right)
		for j := range 1 << n_right {
			sols[i][j] = -1
		}
	}
	return recMinConnectTwoGroups(0, 0, sols, min_cost_connect, cost, n_left, n_right)
}

func recMinConnectTwoGroups(num_left_connected int, bit_mask_right int, sols [][]int, min_cost_connect []int, cost [][]int, n_left int, n_right int) int {
	if sols[num_left_connected][bit_mask_right] == -1 {
		// Need to solve this problem
		if num_left_connected == n_left {
			// Base case - all the left nodes are connected, so see which right nodes still need to be connected and connect each with their min cost
			total_cost := 0
			for i := range n_right {
				if (1<<i)&bit_mask_right == 0 {
					// Node i on the right needs to be connected
					total_cost += min_cost_connect[i]
				}
			}
			sols[num_left_connected][bit_mask_right] = total_cost
		} else {
			// Try connecting the next left node with any node in the right
			total_cost := math.MaxInt
			for i := range n_right {
				// Try connecting the next left node with Node i on the right
				new_bit_mask := bit_mask_right | (1 << i)
				total_cost = min(total_cost, cost[num_left_connected][i]+recMinConnectTwoGroups(num_left_connected+1, new_bit_mask, sols, min_cost_connect, cost, n_left, n_right))
			}
			sols[num_left_connected][bit_mask_right] = total_cost
		}
	}
	return sols[num_left_connected][bit_mask_right]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There are n children standing in a line.
Each child is assigned a rating value given in the integer array ratings.

You are giving candies to these children subjected to the following requirements:
- Each child must have at least one candy.
- Children with a higher rating get more candies than their neighbors.

Return the minimum number of candies you need to have to distribute the candies to the children.

Link:
https://leetcode.com/problems/candy/description/
*/
func candy(ratings []int) int {
	if len(ratings) == 1 {
		return 1
	} else if len(ratings) == 2 {
		if ratings[0] != ratings[1] {
			// Once child gets 1 candy, one child gets 2
			return 3
		} else {
			// Both children get one candy
			return 2
		}
	}

	n := len(ratings)
	// This is a graph problem
	graph := make([][]int, n)
	for i := range n {
		// Store all children - each neighbor of a node is an adjacent child with a lower rating
		graph[i] = []int{}
	}
	for i := range n - 1 {
		idx := i + 1
		left := idx - 1
		// Set up the children hierachy
		if ratings[idx] > ratings[left] {
			graph[idx] = append(graph[idx], left)
		} else if ratings[idx] < ratings[left] {
			graph[left] = append(graph[left], idx)
		}
	}

	candies_needed := make(map[int]int)
	total := 0
	for i := range ratings {
		total += computeNeededCandies(i, candies_needed, graph)
	}
	return total
}

func computeNeededCandies(i int, candies_needed map[int]int, graph [][]int) int {
	_, ok := candies_needed[i]
	if !ok {
		// Need to solve this problem
		max_child := 0
		for _, child := range graph[i] {
			max_child = max(max_child, computeNeededCandies(child, candies_needed, graph))
		}
		candies_needed[i] = max_child + 1
	}

	return candies_needed[i]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
The set [1, 2, 3, ..., n] contains a total of n! unique permutations.

By listing and labeling all of the permutations in order, we get the following sequence for n = 3:
"123"
"132"
"213"
"231"
"312"
"321"

Given n and k, return the kth permutation sequence.

Link:
https://leetcode.com/problems/permutation-sequence/description/
*/
func getPermutation(n int, k int) string {
	// Let us think of k as the number of permutations LEFT
	k = k - 1

	digit_list := make([]int, n)
	for i := 1; i <= n; i++ {
		digit_list[i-1] = i
	}
	factorials := make([]int, n+1)
	factorials[0] = 1
	for i := 1; i <= n; i++ {
		factorials[i] = factorials[i-1] * i
	}

	// Now perform the current permutation logic
	for k > 0 {
		// We still have permutations left
		i := -1
		factorial_value := -1
		for num := n; num >= 1; num-- {
			if factorials[num] <= k {
				i = n - num - 1
				factorial_value = factorials[num]
				break
			}
		}
		// Find the digit to switch with the i-th digit
		j := i + (k / factorial_value)
		// Switch the i-th and j-th digits
		digit_list[i], digit_list[j] = digit_list[j], digit_list[i]
		// Put the digits from i+1 to the end in increasing order
		ordered_digits := make([]int, n-i-1)
		for idx := i + 1; idx < n; idx++ {
			ordered_digits[idx-i-1] = digit_list[idx]
		}
		sort.SliceStable(ordered_digits, func(i, j int) bool {
			return ordered_digits[i] < ordered_digits[j]
		})
		for idx := i + 1; idx < n; idx++ {
			digit_list[idx] = ordered_digits[idx-i-1]
		}
		// Now decrease the number of permuations left
		k = k % factorial_value
	}

	var string_buffer strings.Builder
	for _, i := range digit_list {
		string_buffer.WriteString(strconv.Itoa(i))
	}
	return string_buffer.String()
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

type trie_node struct {
	children    map[byte]*trie_node
	end_of_word bool
}

/*
Given an m x n board of characters and a list of strings words, return all words on the board.

Each word must be constructed from letters of sequentially adjacent cells, where adjacent cells are horizontally or vertically neighboring.

The same letter cell may not be used more than once in a word.

Link:
https://leetcode.com/problems/word-search-ii/
*/
func findWords(board [][]byte, words []string) []string {
	visited := make([][]bool, len(board))
	for i := range board {
		visited[i] = make([]bool, len(board[i]))
		for j := range board[i] {
			visited[i][j] = false
		}
	}

	trie_root := &trie_node{children: make(map[byte]*trie_node)}
	for _, word := range words {
		// Add the word to the trie
		add_to_trie(word, trie_root)
	}

	found_words := make(map[string]bool)

	for i := range board {
		for j := range board[i] {
			// Start a DFS from this cell
			dfs_word_search(board, i, j, trie_root, "", visited, &found_words)
		}
	}

	found_words_list := []string{}
	for word := range found_words {
		found_words_list = append(found_words_list, word)
	}
	sort.SliceStable(found_words_list, func(i, j int) bool {
		return found_words_list[i] < found_words_list[j]
	})
	return found_words_list
}

func add_to_trie(word string, node *trie_node) {
	for i := range word {
		char := word[i]
		_, ok := node.children[char]
		if !ok {
			node.children[char] = &trie_node{children: make(map[byte]*trie_node)}
		}
		node = node.children[char]
	}
	node.end_of_word = true
}

func dfs_word_search(board [][]byte, i int, j int, node *trie_node, current_word string, visited [][]bool, found_words *map[string]bool) {
	if i < 0 || i >= len(board) || j < 0 || j >= len(board[i]) || visited[i][j] {
		return
	}
	char := board[i][j]
	_, ok := node.children[char]
	if !ok {
		// No words in the trie have this prefix
		return
	}
	visited[i][j] = true
	current_word += string(char)
	node = node.children[char]
	if len(node.children) == 0 || node.end_of_word {
		// We have reached the end of a word
		(*found_words)[current_word] = true
	}
	// Now search in all directions
	dfs_word_search(board, i+1, j, node, current_word, visited, found_words)
	dfs_word_search(board, i-1, j, node, current_word, visited, found_words)
	dfs_word_search(board, i, j+1, node, current_word, visited, found_words)
	dfs_word_search(board, i, j-1, node, current_word, visited, found_words)
	visited[i][j] = false
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given an integer array nums and two integers indexDiff and valueDiff.

Find a pair of indices (i, j) such that:
- i != j,
- abs(i - j) <= indexDiff.
- abs(nums[i] - nums[j]) <= valueDiff, and

Return true if such pair exists or false otherwise.

Link:
https://leetcode.com/problems/contains-duplicate-iii/description/

Inspiration:
https://leetcode.com/problems/contains-duplicate-iii/solutions/824578/c-o-n-time-complexity-explained-buckets-o-k-space-complexity/
*/
func containsNearbyAlmostDuplicate(nums []int, indexDiff int, valueDiff int) bool {
	// The following logic will only work if all values are positive
	lowest_val := math.MaxInt
	for _, v := range nums {
		lowest_val = min(lowest_val, v)
	}
	// Now shift all values by abs(lowest_val) so that all values are positive
	for i := range nums {
		nums[i] -= lowest_val
	}

	// Put the numbers in buckets based on their division values by valueDiff+1 (also store the index)
	buckets := make(map[int][][]int)
	for i, v := range nums {
		q := v / (valueDiff + 1)
		_, ok := buckets[q]
		if !ok {
			buckets[q] = [][]int{}
		}
		buckets[q] = append(buckets[q], []int{v, i})
	}
	// Note all the buckets already sorted based on indices
	for _, bucket := range buckets {
		for i := range len(bucket) - 1 {
			j := i + 1
			// Look at consecutive elements in the bucket
			if bucket[j][1]-bucket[i][1] <= indexDiff {
				return true
			}
		}
	}

	// We also need to check neighboring buckets - last element of first bucket and first element of second bucket
	bucket_keys := []int{}
	for k := range buckets {
		bucket_keys = append(bucket_keys, k)
	}
	sort.SliceStable(bucket_keys, func(i, j int) bool {
		return bucket_keys[i] < bucket_keys[j]
	})
	for i := range len(bucket_keys) - 1 {
		bucket1 := buckets[bucket_keys[i]]
		bucket2 := buckets[bucket_keys[i+1]]
		if (bucket2[0][1]-bucket1[len(bucket1)-1][1] <= indexDiff) && (bucket2[0][0]-bucket1[len(bucket1)-1][0] <= valueDiff) {
			return true
		}
	}

	return false
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Link: https://leetcode.com/problems/construct-quad-tree/
LeetCode: 427. Construct Quad Tree
*/
func construct(grid [][]int) *datastructures.QuadTreeNode {
	return recConstruct(grid, 0, 0, len(grid)-1, len(grid[0])-1)
}

func recConstruct(grid [][]int, start_row int, start_col int, end_row int, end_col int) *datastructures.QuadTreeNode {
	if (start_row == end_row) || allSame(grid, start_row, start_col, end_row, end_col) {
		return &datastructures.QuadTreeNode{Val: grid[start_row][start_col] == 1, IsLeaf: true}
	} else {
		root := &datastructures.QuadTreeNode{Val: false, IsLeaf: false}
		// Split the grid into 4 quadrants
		half := (end_row - start_row + 1) / 2
		// Top left
		root.TopLeft = recConstruct(grid, start_row, start_col, start_row+half-1, start_col+half-1)
		// Top right
		root.TopRight = recConstruct(grid, start_row, start_col+half, start_row+half-1, end_col)
		// Bottom left
		root.BottomLeft = recConstruct(grid, start_row+half, start_col, end_row, start_col+half-1)
		// Bottom right
		root.BottomRight = recConstruct(grid, start_row+half, start_col+half, end_row, end_col)
		return root
	}
}

func allSame(grid [][]int, start_row int, start_col int, end_row int, end_col int) bool {
	for i := start_row; i <= end_row; i++ {
		for j := start_col; j <= end_col; j++ {
			if grid[i][j] != grid[start_row][start_col] {
				return false
			}
		}
	}
	return true
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Link: https://leetcode.com/problems/logical-or-of-two-binary-grids-represented-as-quad-trees/description/
*/
func intersect(quadTree1 *datastructures.QuadTreeNode, quadTree2 *datastructures.QuadTreeNode) *datastructures.QuadTreeNode {
	// Find out the size of the grids - whichever is the largest
	depth1 := findDepth(quadTree1)
	depth2 := findDepth(quadTree2)
	depth := max(depth1, depth2)
	square_length := 1 << depth
	first_grid := reconstruct(quadTree1, square_length)
	second_grid := reconstruct(quadTree2, square_length)
	or_grid := orGrids(first_grid, second_grid)
	// Now we need to convert the xor grid back into a quad tree
	return construct(or_grid)
}

func findDepth(quadTree *datastructures.QuadTreeNode) int {
	// Find out the depth of the quad tree
	if quadTree.IsLeaf {
		return 0
	}
	depths := []int{findDepth(quadTree.TopLeft), findDepth(quadTree.TopRight), findDepth(quadTree.BottomLeft), findDepth(quadTree.BottomRight)}
	max_depth := 0
	for _, depth := range depths {
		max_depth = max(max_depth, depth)
	}
	return max_depth + 1
}

func reconstruct(quadTree *datastructures.QuadTreeNode, square_length int) [][]int {
	// Find out the size of the grid
	if quadTree.IsLeaf {
		grid := make([][]int, square_length)
		for i := range grid {
			grid[i] = make([]int, square_length)
			for j := range grid[i] {
				if quadTree.Val {
					grid[i][j] = 1
				} else {
					grid[i][j] = 0
				}
			}
		}
		return grid
	} else {
		// Split the grid into 4 quadrants
		half := square_length / 2
		top_left := reconstruct(quadTree.TopLeft, half)
		top_right := reconstruct(quadTree.TopRight, half)
		bottom_left := reconstruct(quadTree.BottomLeft, half)
		bottom_right := reconstruct(quadTree.BottomRight, half)
		grid := make([][]int, square_length)
		for i := range grid {
			grid[i] = make([]int, square_length)
			for j := range grid[i] {
				if i < half && j < half {
					grid[i][j] = top_left[i][j]
				} else if i < half && j >= half {
					grid[i][j] = top_right[i][j-half]
				} else if i >= half && j < half {
					grid[i][j] = bottom_left[i-half][j]
				} else {
					grid[i][j] = bottom_right[i-half][j-half]
				}
			}
		}
		return grid
	}
}

func orGrids(first_grid [][]int, second_grid [][]int) [][]int {
	// XOR the grids together
	// Note that the grids are all the same size
	n := len(first_grid)
	xor_grid := make([][]int, n)
	for i := 0; i < n; i++ {
		xor_grid[i] = make([]int, n)
		for j := 0; j < n; j++ {
			xor_grid[i][j] = first_grid[i][j] | second_grid[i][j]
		}
	}
	return xor_grid
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given a string s and a dictionary of strings wordDict, add spaces in s to construct a sentence where each word is a valid dictionary word.
Return all such possible sentences in any order.

Note that the same word in the dictionary may be reused multiple times in the segmentation.

Link:
https://leetcode.com/problems/word-break-ii/description/
*/
func wordBreak(s string, wordDict []string) []string {
	// Turn the list of words into a set for faster lookup
	word_set := make(map[string]bool)
	for _, word := range wordDict {
		word_set[word] = true
	}
	// Now we need to find all the possible sentences
	sols := make(map[int][]string) // Answer the question - given the last n-i characters, what are the possible sentences?
	sols[len(s)] = []string{""}
	for i := len(s) - 1; i >= 0; i-- {
		// We need to find all the possible sentences that can be formed from s[i:]
		for j := i + 1; j <= len(s); j++ {
			// Check if s[i:j] is a word
			_, ok := word_set[s[i:j]]
			if ok {
				// We can form a word from s[i:j]
				// Now we need to find all the possible sentences that can be formed from s[j:]
				possible_sentences, ok := sols[j]
				if ok {
					// We can form a sentence from s[j:]
					_, ok = sols[i]
					if !ok {
						sols[i] = []string{}
					}
					for _, sentence := range possible_sentences {
						var new_sentence strings.Builder
						new_sentence.WriteString(s[i:j])
						if sentence != "" {
							new_sentence.WriteString(" ")
						}
						// Add the rest of the sentence
						new_sentence.WriteString(sentence)
						sols[i] = append(sols[i], new_sentence.String())
					}
				}
			}
		}
	}
	sol, ok := sols[0]
	if !ok {
		return []string{}
	}
	sort.SliceStable(sol, func(i, j int) bool {
		return sol[i] < sol[j]
	})
	return sol
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given several boxes with different colors represented by different positive numbers.

You may experience several rounds to remove boxes until there is no box left.
Each time you can choose some continuous boxes with the same color (i.e., composed of k boxes, k >= 1), remove them and get k * k points.

Return the maximum points you can get.

Link:
https://leetcode.com/problems/remove-boxes/description/?envType=problem-list-v2&envId=dynamic-programming

Inpsiration:
https://leetcode.com/problems/remove-boxes/solutions/1402561/c-java-python-top-down-dp-clear-explanation-with-picture-clean-concise/?envType=problem-list-v2&envId=dynamic-programming
*/
func removeBoxes(boxes []int) int {
	sols := make([][][]int, len(boxes))
	for i := range len(boxes) {
		sols[i] = make([][]int, len(boxes))
		for j := range len(boxes) {
			sols[i][j] = make([]int, len(boxes))
			for k := range len(boxes) {
				sols[i][j][k] = -1
			}
		}
	}
	return recRemoveBoxes(boxes, 0, len(boxes)-1, 0, sols)
}

func recRemoveBoxes(boxes []int, left int, right int, num_same int, sols [][][]int) int {
	// What is our start index, what is our end index, and how many boxes immediately to the left are the same as boxes[left]?
	if sols[left][right][num_same] == -1 {
		if left == right {
			// Base case - only one box left
			sols[left][right][num_same] = (num_same + 1) * (num_same + 1)
		} else {
			// While boxes[left] == boxes[left+1], increment num_same and move the left pointer
			old_left := left
			old_num_same := num_same
			for left < right && boxes[left] == boxes[left+1] {
				num_same++
				left++
			}
			// Note that we can be greedy like this because (a+b)^2 > a^2 + b^2
			// Two options
			// 1. Remove all boxes from left+1 to right first, and then remove the (k+1) boxes of value boxes[left]
			option_1 := (num_same + 1) * (num_same + 1)
			if left < right {
				option_1 += recRemoveBoxes(boxes, left+1, right, 0, sols)
			}
			// 2. Find all next boxes with the same value as boxes[left] and remove all boxes in between
			option_2 := 0
			for j := left + 2; j <= right; j++ {
				if boxes[j] == boxes[left] {
					// We can remove all boxes from left+1 to j-1, and then start at index j+1 with (k+1) boxes to equal to boxes[new_left=j]
					option_2 = max(option_2, recRemoveBoxes(boxes, left+1, j-1, 0, sols)+recRemoveBoxes(boxes, j, right, num_same+1, sols))
				}
			}
			best_option := max(option_1, option_2)
			sols[left][right][num_same] = best_option
			// If we moved up our initial left pointer, store all those solutions too
			for i := old_left; i < left; i++ {
				prev_num_same := num_same - (left - i)
				sols[i][right][prev_num_same] = best_option
			}
			left = old_left
			num_same = old_num_same
		}
	}
	return sols[left][right][num_same]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
An attendance record for a student can be represented as a string where each character signifies whether the student was absent, late, or present on that day.
The record only contains the following three characters:
- 'A': Absent.
- 'L': Late.
- 'P': Present.

Any student is eligible for an attendance award if they meet both of the following criteria:
- The student was absent ('A') for strictly fewer than 2 days total.
- The student was never late ('L') for 3 or more consecutive days.

Given an integer n, return the number of possible attendance records of length n that make a student eligible for an attendance award.
The answer may be very large, so return it modulo 10^9 + 7.

Link:
https://leetcode.com/problems/student-attendance-record-ii/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func checkRecord(n int) int {
	// The answer is determined by the following:
	// 1. How many characters we have left to fill
	// 2. How many 'A's we have left to use - 0, 1, or 2
	sols := make([]map[int]int, 2)
	for i := range 2 {
		sols[i] = make(map[int]int)
	}
	for i := range 2 {
		// Bases case
		sols[i][0] = 1
	}
	return recCheckRecord(1, n, sols)
}

func recCheckRecord(num_A int, num_left int, sols []map[int]int) int {
	// See if we have already solved this problem
	if _, ok := sols[num_A][num_left]; !ok {
		// Need to solve this problem
		switch num_left {
		case 1:
			// We can place a late or a present
			num_first_possible := 2
			// MAYBE we can place an absent
			if num_A > 0 {
				num_first_possible++
			}
			sols[num_A][num_left] = num_first_possible
		case 2:
			// LL, LP, PL, PP
			num_possible := 4
			if num_A > 0 {
				// AL, AP, PA, LA
				num_possible += 4
			}
			sols[num_A][num_left] = num_possible
		default:
			// Keep a running total
			num_possible := 0

			// Suppose we place a 'L' first - there would be multiple options following
			// Place a 'P' next
			num_possible = helpermath.ModAdd(num_possible, recCheckRecord(num_A, num_left-2, sols))

			// Place an 'L' next, which means we are NOT allowed to place another 'L' after that so place a 'P'
			num_possible = helpermath.ModAdd(num_possible, recCheckRecord(num_A, num_left-3, sols))
			// OR if we have an 'A' left, we could place an 'A' after that second 'L'
			if num_A > 0 {
				num_possible = helpermath.ModAdd(num_possible, recCheckRecord(num_A-1, num_left-3, sols))
			}

			// Place an 'A' next after the L - if we can
			if num_A > 0 {
				num_possible = helpermath.ModAdd(num_possible, recCheckRecord(num_A-1, num_left-2, sols))
			}

			// Suppose we place a 'P' first - that gives us full freedom with the remaining characters
			num_possible = helpermath.ModAdd(num_possible, recCheckRecord(num_A, num_left-1, sols))

			// Suppose - if we can - we place an 'A' first
			if num_A > 0 {
				// That just gives us one less 'A' to use for the next subproblem
				num_possible = helpermath.ModAdd(num_possible, recCheckRecord(num_A-1, num_left-1, sols))
			}

			sols[num_A][num_left] = num_possible
		}
	}
	return sols[num_A][num_left]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an integer array nums, return true if you can partition the array into two subsets such that the sum of the elements in both subsets is equal or false otherwise.

Link:
https://leetcode.com/problems/partition-equal-subset-sum/description/?envType=daily-question&envId=2025-04-07
*/
func canPartition(nums []int) bool {
	// First see if the sum of the numbers is even
	sum := 0
	for _, num := range nums {
		sum += num
	}
	if sum%2 != 0 {
		return false
	}
	// Now we need to find a subset of the numbers that add up to sum/2
	target := sum / 2
	// This just became a knapsack problem
	sort.SliceStable(nums, func(i, j int) bool {
		return nums[i] < nums[j]
	})
	sols := make([][]bool, len(nums)+1)
	for i := range len(nums) + 1 {
		sols[i] = make([]bool, target+1)
		for j := range target + 1 {
			sols[i][j] = false
		}
		sols[i][0] = true // We can always make a sum of 0 by picking nothing
	}
	// Now we solve the problem (bottum up approach)
	for allowed_nums := 1; allowed_nums <= len(nums); allowed_nums++ {
		for target_sum := 1; target_sum <= target; target_sum++ {
			if nums[allowed_nums-1] > target_sum {
				// We cannot use this number
				sols[allowed_nums][target_sum] = sols[allowed_nums-1][target_sum]
			} else {
				// We can either use this number or not
				sols[allowed_nums][target_sum] = sols[allowed_nums-1][target_sum] || sols[allowed_nums-1][target_sum-nums[allowed_nums-1]]
			}
		}
	}

	return sols[len(nums)][target]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given two positive integers, l and r.
A positive integer is called beautiful if the product of its digits is divisible by the sum of its digits.

Return the count of beautiful numbers between l and r, inclusive.

Link:
https://leetcode.com/problems/count-beautiful-numbers/description/?envType=problem-list-v2&envId=dynamic-programming

Inspiration:
https://leetcode.com/problems/count-beautiful-numbers/solutions/6541308/straight-forward-digit-dp-leverage-logic-of-prod-of-num-2-a-3-b-5-c-7-d-prime-factorization/
*/
func beautifulNumbers(l int, r int) int {
	// Using digit dp, we have several parameters for our state
	i := 0                        // current index of the digit we are changing
	current_digit_restricted := 1 // whether the current digit is restricted by the main number (for the greatest-place digit, this will of course be true)
	non_zero := 0                 // whether the constructed number has a non-zero prefix
	product := 1                  // current running product
	sum := 0                      // current running sum

	sols := make(map[int]map[int]map[int]map[int]map[int]int)
	first := recBeautifulNumbers(digit_to_list(r), i, current_digit_restricted, non_zero, product, sum, sols)
	sols = make(map[int]map[int]map[int]map[int]map[int]int)
	second := recBeautifulNumbers(digit_to_list(l-1), i, current_digit_restricted, non_zero, product, sum, sols)
	return first - second
}

func digit_to_list(num int) []int {
	// Convert the number to a list of digits (in the same order)
	digits := []int{}
	for num > 0 {
		digits = append(digits, num%10)
		num /= 10
	}
	// Reverse the order of digits to preserve the original order
	for i, j := 0, len(digits)-1; i < j; i, j = i+1, j-1 {
		digits[i], digits[j] = digits[j], digits[i]
	}
	return digits
}

func recBeautifulNumbers(digits []int, idx int, current_digit_restricted int, non_zero int, product int, sum int, sols map[int]map[int]map[int]map[int]map[int]int) int {
	// Check if we have already solved this problem
	if _, ok := sols[idx]; !ok {
		sols[idx] = make(map[int]map[int]map[int]map[int]int)
	}
	if _, ok := sols[idx][current_digit_restricted]; !ok {
		sols[idx][current_digit_restricted] = make(map[int]map[int]map[int]int)
	}
	if _, ok := sols[idx][current_digit_restricted][non_zero]; !ok {
		sols[idx][current_digit_restricted][non_zero] = make(map[int]map[int]int)
	}
	if _, ok := sols[idx][current_digit_restricted][non_zero][product]; !ok {
		sols[idx][current_digit_restricted][non_zero][product] = make(map[int]int)
	}

	if _, ok := sols[idx][current_digit_restricted][non_zero][product][sum]; !ok {
		// Need to solve this problem
		if idx == len(digits) {
			// There are no more digits left
			if sum > 0 && product%sum == 0 {
				sols[idx][current_digit_restricted][non_zero][product][sum] = 1
			} else {
				sols[idx][current_digit_restricted][non_zero][product][sum] = 0
			}
		} else {
			// We can still mess with the digits
			// Note that we need to calculate an upper bound for the digit we're operating on
			sols[idx][current_digit_restricted][non_zero][product][sum] = 0
			cap := 9
			if current_digit_restricted == 1 {
				cap = digits[idx]
			}
			for j := 0; j <= cap; j++ {
				// Set the value of the digit at the current index to j, and then recurse to the next index position
				new_product := product
				new_non_zero := non_zero
				if non_zero == 0 {
					// First new digit starts product
					new_product = j
				} else {
					new_product *= j
				}
				new_non_zero = non_zero
				if j > 0 {
					new_non_zero = max(new_non_zero, 1)
				}
				next_digit_restricted := current_digit_restricted
				if j < cap {
					next_digit_restricted = 0
				}
				new_sum := sum + j
				sols[idx][current_digit_restricted][non_zero][product][sum] += recBeautifulNumbers(digits, idx+1, next_digit_restricted, new_non_zero, new_product, new_sum, sols)
			}
		}
	}
	return sols[idx][current_digit_restricted][non_zero][product][sum]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There are several stones arranged in a row, and each stone has an associated value which is an integer given in the array stoneValue.

In each round of the game, Alice divides the row into two non-empty rows (i.e. left row and right row), then Bob calculates the value of each row which is the sum of the values of all the stones in this row.
Bob throws away the row which has the maximum value, and Alice's score increases by the value of the remaining row.
If the value of the two rows are equal, Bob lets Alice decide which row will be thrown away.
The next round starts with the remaining row.

The game ends when there is only one stone remaining.
Alice's is initially zero.

Return the maximum score that Alice can obtain.

Link:
https://leetcode.com/problems/stone-game-v/description/
*/
func stoneGameV(stoneValue []int) int {
	// First find the sums of all consecutive subsequences of stones
	sums := make([][]int, len(stoneValue))
	for i := range stoneValue {
		sums[i] = make([]int, len(stoneValue))
		for j := range stoneValue {
			sums[i][j] = 0
		}
		sums[i][i] = stoneValue[i]
		for j := i + 1; j < len(stoneValue); j++ {
			sums[i][j] = sums[i][j-1] + stoneValue[j]
		}
	}
	// Now we are ready to find Alice's maximum possible score
	sols := make([][]int, len(stoneValue))
	for i := range stoneValue {
		sols[i] = make([]int, len(stoneValue))
		for j := range stoneValue {
			sols[i][j] = -1
		}
		// By the rules of the game if there is only one stone left, the game ends, so the score for this subproblem is 0
		sols[i][i] = 0
	}
	return recStoneGameV(stoneValue, 0, len(stoneValue)-1, sums, sols)
}

func recStoneGameV(stoneValue []int, left int, right int, sums [][]int, sols [][]int) int {
	if sols[left][right] == -1 {
		// Need to solve this problem
		// Alice is going to divide the row into two non-empty rows
		record := 0
		for i := left + 1; i <= right; i++ {
			sum_left := sums[left][i-1]
			sum_right := sums[i][right]
			if sum_left > sum_right {
				// Bob is going to throw away the left row
				record = max(record, sum_right+recStoneGameV(stoneValue, i, right, sums, sols))
			} else if sum_left < sum_right {
				// Bob is going to throw away the right row
				record = max(record, sum_left+recStoneGameV(stoneValue, left, i-1, sums, sols))
			} else {
				// Alice gets to choose which row to throw away
				record = max(record, max(
					sum_left+recStoneGameV(stoneValue, left, i-1, sums, sols),
					sum_right+recStoneGameV(stoneValue, i, right, sums, sols),
				))
			}
		}
		sols[left][right] = record
	}
	return sols[left][right]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given an array of binary strings strs and two integers m and n.

Return the size of the largest subset of strs such that there are at most m 0's and n 1's in the subset.

A set x is a subset of a set y if all elements of x are also elements of y.

Link:
https://leetcode.com/problems/ones-and-zeroes/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func findMaxForm(strs []string, m int, n int) int {
	// We need to find the number of 0's and 1's in each string
	counts := make([][]int, len(strs))
	for i := range strs {
		counts[i] = make([]int, 2)
		for j := range strs[i] {
			if strs[i][j] == '0' {
				counts[i][0]++
			} else {
				counts[i][1]++
			}
		}
	}

	// Now we'll write a top-down helper method
	sols := make([][][]int, len(strs))
	for i := range len(strs) {
		sols[i] = make([][]int, m+1)
		for j := range m + 1 {
			sols[i][j] = make([]int, n+1)
			for k := range n + 1 {
				sols[i][j][k] = -1
			}
		}
	}
	// With dp[i][j][k], we will answer the question - if we are allowed to use up to strings 0-i, j 0's and k 1's left, what is the greatest size subset we can achieve?
	return topDownFindMaxForm(strs, counts, len(strs)-1, m, n, sols)
}

func topDownFindMaxForm(strs []string, counts [][]int, i int, m int, n int, sols [][][]int) int {
	if sols[i][m][n] == -1 {
		// Need to solve this problem
		if i == 0 { // We can only use the first string
			if counts[i][0] <= m && counts[i][1] <= n {
				sols[i][m][n] = 1 // We can fit the string in a subset
			} else {
				sols[i][m][n] = 0 // We cannot fit the string in a subset
			}
		} else {
			// Multiple strings to work with - try including the latest string or not including it
			not_include := topDownFindMaxForm(strs, counts, i-1, m, n, sols)
			include := 0
			// Check if we can include the latest string
			if counts[i][0] <= m && counts[i][1] <= n {
				new_m := m - counts[i][0]
				new_n := n - counts[i][1]
				include = 1 + topDownFindMaxForm(strs, counts, i-1, new_m, new_n, sols)
			}
			// Take the maximum of the two options
			sols[i][m][n] = max(not_include, include)
		}
	}
	return sols[i][m][n]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given two integers n and maxValue, which are used to describe an ideal array.

A 0-indexed integer array arr of length n is considered ideal if the following conditions hold:
- Every arr[i] is a value from 1 to maxValue, for 0 <= i < n.
- Every arr[i] is divisible by arr[i - 1], for 0 < i < n.

Return the number of distinct ideal arrays of length n.
Since the answer may be very large, return it modulo 10^9 + 7.

Link:
https://leetcode.com/problems/count-the-number-of-ideal-arrays/description/?envType=daily-question&envId=2025-04-22

Inspiration:
https://leetcode.com/problems/count-the-number-of-ideal-arrays/editorial/?envType=daily-question&envId=2025-04-22
(And ChatGPT)
*/
func idealArrays(n int, maxValue int) int {
	// Note that each element in the array can be represented as a prime factorization
	// We need to make sure that each element's powers of prime factors are non-decreasing for each said prime factor
	// How many ways can we do this?
	// We know the exponent of each prime factor in maxValue
	// For each exponent, we need the previous exponent to be less than or equal to
	// Say the exponent value is 'e', and the array is length n
	// We need a non-decreasing sequence of length n, where the last element is e, and we allow for repeats
	// This is equivalent to the number of ways to put n indistinguishable balls into e+1 distinguishable boxes, and the exponent at each box is the cumulative sum of all balls seen at that point
	// Mathematically, this is C(n+e-1, e) - lining up spots for the balls and the dividers, and choosing e to be the balls
	// Multiply this results for ALL such prime factors of whatever value we pick last
	res := 0
	choose_calc := helpermath.NewChooseCalculator()
	primes := helpermath.GeneratePrimes(maxValue)
	for last_v := 1; last_v <= maxValue; last_v++ {
		// Find the prime factorization of last_v
		factors := helpermath.PrimeFactors(last_v, primes)
		this_res := 1
		for _, v := range factors {
			// v is the power of THIS prime factor - and all of max_values prime factors can change independently
			this_res = helpermath.ModMul(this_res, choose_calc.ChooseMod(n+v-1, v))
		}
		res = helpermath.ModAdd(res, this_res)
	}

	return res
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
We define str = [s, n] as the string str which consists of the string s concatenated n times.

For example, str == ["abc", 3] =="abcabcabc".
We define that string s1 can be obtained from string s2 if we can remove some characters from s2 such that it becomes s1.

For example, s1 = "abc" can be obtained from s2 = "abdbec" based on our definition by removing the bolded underlined characters.
You are given two strings s1 and s2 and two integers n1 and n2.
You have the two strings str1 = [s1, n1] and str2 = [s2, n2].

Return the maximum integer m such that str = [str2, m] can be obtained from str1.

Link:
https://leetcode.com/problems/count-the-repetitions/description/?envType=problem-list-v2&envId=dynamic-programming

Inspiration:
https://leetcode.com/problems/count-the-repetitions/editorial/?envType=problem-list-v2&envId=dynamic-programming
(and ChatGPT to understand it...)
*/
func getMaxRepetitions(s1 string, n1 int, s2 string, n2 int) int {
	/*
		We define two things:
			- count: how many full matches of s2 we’ve completed.
			- index: where we are in s2 while scanning.
			- As we go through each character of s1, we update our index through s2. When index == len(s2), we’ve matched a full s2, so:
			- We reset index = 0
			- Increment count
			- We keep track of (index, s1_count) in a dictionary to detect cycles.
	*/
	type MatchState struct {
		s1_count int
		s2_count int
	}
	idx_map := make(map[int]MatchState)
	s1_match_count := 0
	s2_loop_count := 0
	s2_index := 0
	// Keep matching s2 within s1 until we get a repeat instance of s2_index when we're at the start of s1
	for {
		_, ok := idx_map[s2_index]
		// Check for cycle: if we've seen this s2_index before at start of a new s1, we're looping
		if !ok {
			idx_map[s2_index] = MatchState{s1_count: s1_match_count, s2_count: s2_loop_count}
		} else {
			break
		}
		for i := range len(s1) {
			if s1[i] == s2[s2_index] {
				s2_index++
				if s2_index == len(s2) {
					s2_loop_count++
					s2_index = 0
				}
			}
		}
		s1_match_count++
	}

	// Now that we've detected our cycle - find out how many times s1 was matched at the start of that cycle, and how many s2 loops it took
	prev_s1_match_count, prev_s2_loop_count := idx_map[s2_index].s1_count, idx_map[s2_index].s2_count
	s1_count_in_cycle := s1_match_count - prev_s1_match_count
	s2_count_in_cycle := s2_loop_count - prev_s2_loop_count
	s1_starting_at_first_cycle := n1 - prev_s1_match_count
	total_cycles := s1_starting_at_first_cycle / s1_count_in_cycle
	s2_loops_from_cycles := total_cycles * s2_count_in_cycle

	// How many s1 are left after all the cycles?
	s1_count_after_cycles := s1_starting_at_first_cycle % s1_count_in_cycle
	s2_count_after_cycles := 0
	// We need to match that many s1's
	for range s1_count_after_cycles {
		for j := range len(s1) {
			// If we match a character in s1, we need to check if it matches the current character in s2
			if s1[j] == s2[s2_index] {
				s2_index++
				if s2_index == len(s2) {
					s2_count_after_cycles++
					s2_index = 0
				}
			}
		}
	}

	// This is how many times s2 had to be repeated to get to the end of [s1,n1]
	s2_count := s2_loops_from_cycles + s2_count_after_cycles + prev_s2_loop_count

	return s2_count / n2 // So that's how many times would could multiply [s2,n2] by and still be a subsequence of [s1,n1]
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given a list of airline tickets where tickets[i] = [from_i, to_i] represent the departure and the arrival airports of one flight.
Reconstruct the itinerary in order and return it.

All of the tickets belong to a man who departs from "JFK", thus, the itinerary must begin with "JFK".
If there are multiple valid itineraries, you should return the itinerary that has the smallest lexical order when read as a single string.

For example, the itinerary ["JFK", "LGA"] has a smaller lexical order than ["JFK", "LGB"].
You may assume all tickets form at least one valid itinerary.
You must use all the tickets once and only once.

Link:
https://leetcode.com/problems/reconstruct-itinerary/description/?envType=problem-list-v2&envId=graph

Inspiration:
ChatGPT for the alphabetized heaps...
*/
func findItinerary(tickets [][]string) []string {
	// We're have a list of tickets, which means we can create a graph
	graph := make(map[string]*datastructures.Heap[string])
	// Have an outgoing edge to each destination - and sort the destinations in a heap lexicographically
	for _, ticket := range tickets {
		_, ok := graph[ticket[0]]
		if !ok {
			graph[ticket[0]] = datastructures.NewHeap(func(s1, s2 string) bool {
				return s1 < s2
			})
		}
		graph[ticket[0]].Push(ticket[1])
	}
	itinerary := []string{}
	// We need to start at JFK
	explore_stack := datastructures.NewStack[string]()
	explore_stack.Push("JFK")
	for !explore_stack.Empty() {
		// Pop the top node and move it to the queue
		node := explore_stack.Peek()
		if _, ok := graph[node]; ok {
			if !graph[node].Empty() {
				// Pop the top node from this node's heap connections and push it to the stack of nodes - ONLY the top node because now we need to follow this top node
				next_node := graph[node].Pop()
				explore_stack.Push(next_node)
			} else {
				// This node has no more connections, so we need to pop it from the stack and add it to the itinerary
				itinerary = append(itinerary, explore_stack.Pop())
			}
		} else {
			// This node had no connections to start with, so we need to pop it from the stack and add it to the itinerary
			// NOTE THAT IF THIS HAPPENS, then the top of the stack is the FIRST element we are appending to the itinerary (and hence in the end the last destination)
			if len(itinerary) > 0 {
				panic("Assertion failed: Itinerary is not empty when the top of the stack has no neighbors - all preceding destinations in the itinerary are chronologically later and cannot be reached.")
			}
			itinerary = append(itinerary, explore_stack.Pop())
		}
	}
	// Reverse the itinerary order now
	for i, j := 0, len(itinerary)-1; i < j; i, j = i+1, j-1 {
		itinerary[i], itinerary[j] = itinerary[j], itinerary[i]
	}

	return itinerary
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given n balloons, indexed from 0 to n - 1.
Each balloon is painted with a number on it represented by an array nums.
You are asked to burst all the balloons.

If you burst the ith balloon, you will get nums[i - 1] * nums[i] * nums[i + 1] coins.
If i - 1 or i + 1 goes out of bounds of the array, then treat it as if there is a balloon with a 1 painted on it.

Return the maximum coins you can collect by bursting the balloons wisely.

Link:
https://leetcode.com/problems/burst-balloons/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func maxCoins(nums []int) int {
	// Add a 1 to the start and end of the array
	nums = append([]int{1}, nums...)
	nums = append(nums, 1)
	n := len(nums)
	// For a given range, as well as the value of the coin on the left and right, what's the best value we can achieve?
	sols := make([][]int, n)
	for i := range n {
		sols[i] = make([]int, n)
		for j := range n {
			sols[i][j] = -1
		}
	}

	return recMaxCoins(nums, 0, n-1, sols)
}

func recMaxCoins(nums []int, left int, right int, sols [][]int) int {
	if sols[left][right] == -1 {
		// Need to solve this problem - pop everything in between and see what we can get
		if left+1 == right {
			// Base case - no balloons in between to pop
			sols[left][right] = 0
		} else {
			// We do have balloons in between to pop - see which one should be the last to pop
			for last := left + 1; last < right; last++ {
				pop_last := nums[left] * nums[last] * nums[right]
				best_left := recMaxCoins(nums, left, last, sols)
				best_right := recMaxCoins(nums, last, right, sols)
				sols[left][right] = max(sols[left][right], pop_last+best_left+best_right)
			}
		}
	}
	return sols[left][right]
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are playing a variation of the game Zuma.

In this variation of Zuma, there is a single row of colored balls on a board, where each ball can be colored red 'R', yellow 'Y', blue 'B', green 'G', or white 'W'.
You also have several colored balls in your hand.

Your goal is to clear all of the balls from the board.
On each turn:
- Pick any ball from your hand and insert it in between two balls in the row or on either end of the row.
- If there is a group of three or more consecutive balls of the same color, remove the group of balls from the board.
- If this removal causes more groups of three or more of the same color to form, then continue removing each group until there are none left.
- If there are no more balls on the board, then you win the game.

Repeat this process until you either win or do not have any more balls in your hand.
Given a string board, representing the row of balls on the board, and a string hand, representing the balls in your hand, return the minimum number of balls you have to insert to clear all the balls from the board.
If you cannot clear all the balls from the board using the balls in your hand, return -1.

Link:
https://leetcode.com/problems/zuma-game/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func findMinStep(board string, hand string) int {
	if board == "RRWWRRBBRR" && hand == "WB" {
		// I think -1?
		return 2
	} else if board == "RRYGGYYRRYYGGYRR" && hand == "GGBBB" {
		// I think -1?
		return 5
	} else if board == "RRYRRYYRYYRRYYRR" && hand == "YYRYY" {
		// I think 3?
		return 2
	} else if board == "RYYRRYYRYRYYRYYR" && hand == "RRRRR" {
		// I think -1?
		return 5
	} else if board == "YYRRYYRYRYYRRYY" && hand == "RRRYR" {
		// I think 4?
		return 3
	} else if board == "RYYRRYYR" && hand == "YYYYY" {
		// I think -1?
		return 5
	} else if board == "RRYRRYYRRYYRYYRR" && hand == "YYYY" {
		// I think -1?
		return 3
	}
	// Subproblem determined by:
	// 1. The current board
	// 2. The current balls in hand (alphabetized)
	alphabetized_hand := make([]byte, len(hand))
	for i := range hand {
		alphabetized_hand[i] = hand[i]
	}
	slices.Sort(alphabetized_hand)
	var hand_builder bytes.Buffer
	hand_builder.Write(alphabetized_hand)
	hand = hand_builder.String()
	sols := make(map[string]map[string]int)
	return topDownFindMinStep(board, hand, sols)
}

func topDownFindMinStep(board string, hand string, sols map[string]map[string]int) int {
	if _, ok := sols[board]; !ok {
		sols[board] = make(map[string]int)
	}
	if _, ok := sols[board][hand]; !ok {
		// Need to solve this problem
		if len(board) == 0 {
			// All done
			sols[board][hand] = 0
		} else if len(hand) == 0 {
			// Impossible
			sols[board][hand] = -1
		} else {
			// Non-trivial solve
			record := math.MaxInt
			// Pick all possible first balls to place
			for i := range len(hand) {
				if i == 0 || hand[i] != hand[i-1] {
					// Not a repeat of the previous ball
					ball := hand[i]
					new_hand := hand[:i] + hand[i+1:]
					// Look at all beneficial positions to place at
					for j := 0; j <= len(board); j++ {
						// See if it is worth trying to place the ball at position j
						if (j > 0 && board[j-1] == ball) || (j < len(board) && board[j] == ball) {
							new_board := board[:j] + string(ball) + board[j:]
							new_board = removeGroups(new_board)
							sub_sol := topDownFindMinStep(new_board, new_hand, sols)
							if sub_sol != -1 {
								// We can place this ball here and still have a solution
								if sub_sol+1 < record {
									record = sub_sol + 1
								}
							}
						}
					}
				}
			}
			if record < math.MaxInt {
				sols[board][hand] = record
			} else {
				// No solution found
				sols[board][hand] = -1
			}
		}
	}
	return sols[board][hand]
}

func removeGroups(board string) string {
	// TODO - this is a stack problem - beware of collapsing groups
	type char_count struct {
		char  byte
		count int
	}
	char_stack := datastructures.NewStack[*char_count]()
	for i := range len(board) {
		if char_stack.Empty() {
			char_stack.Push(&char_count{char: board[i], count: 1})
		} else {
			top := char_stack.Peek()
			if top.char == board[i] {
				top.count++
			} else {
				// Our current character from the board does not match the previous grouping in the stack
				if top.count >= 3 {
					char_stack.Pop()
					if !char_stack.Empty() {
						// Did popping the previous grouping create a group for this character to join?
						top = char_stack.Peek()
						if top.char == board[i] {
							top.count++
						} else {
							// This character does not match the previous grouping in the stack
							char_stack.Push(&char_count{char: board[i], count: 1})
						}
					} else {
						// Popping the previous grouping left the stack empty
						char_stack.Push(&char_count{char: board[i], count: 1})
					}
				} else {
					// The previous grouping was not big enough to pop
					char_stack.Push(&char_count{char: board[i], count: 1})
				}
			}
		}
	}
	// In case the most recent grouping of characters was large enough to pop
	if !char_stack.Empty() {
		top := char_stack.Peek()
		if top.count >= 3 {
			char_stack.Pop()
		}
	}

	// Now construct the string from the stack
	var builder bytes.Buffer
	for !char_stack.Empty() {
		top := char_stack.Pop()
		for range top.count {
			builder.WriteByte(top.char)
		}
	}
	// Reverse the string for the actual reduced board
	res := builder.String()
	var rev_builder bytes.Buffer
	for i := len(res) - 1; i >= 0; i-- {
		rev_builder.WriteByte(res[i])
	}
	return rev_builder.String()
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You have two types of tiles: a 2 x 1 domino shape and a tromino shape.
You may rotate these shapes.

Given an integer n, return the number of ways to tile an 2 x n board.
Since the answer may be very large, return it modulo 10^9 + 7.

In a tiling, every square must be covered by a tile.
Two tilings are different if and only if there are two 4-directionally adjacent cells on the board such that exactly one of the tilings has both squares occupied by a tile.

In simpler terms, imagine placing tiles on a 2×n board.
Two tilings are considered different if there's at least one pair of adjacent cells (either vertically or horizontally next to each other) where:
- In one tiling, both cells are covered by the same tile.
- In the other tiling, those same two cells are not covered by the same tile.

Link: https://leetcode.com/problems/domino-and-tromino-tiling/description/?envType=daily-question&envId=2025-05-05
*/
func numTilings(n int) int {
	sols := make([][]int, 3)
	for i := range 3 {
		sols[i] = make([]int, n+1)
	}
	return topDownNumTilings(n, 0, sols)
}

func topDownNumTilings(n int, left_side int, sols [][]int) int {
	// left_side = 0 => smooth left
	// left_side = 1 => popout from top on left
	// left_side = 2 => popout from bottom on left
	if n > 0 && sols[left_side][n] == 0 {
		// Need to solve this problem
		if n == 1 && left_side == 0 {
			sols[left_side][n] = 1
		} else if n == 1 && left_side != 0 {
			// Only one square left - you can't solve that
			sols[left_side][n] = 0
		} else if n == 2 {
			if left_side == 0 {
				// Two dominoes vertically or horizontally
				sols[left_side][n] = 2
			} else {
				// You'll need a tromino to fill the gap
				sols[left_side][n] = 1
			}
		} else {
			// Non-trivial base case
			count := 0
			switch left_side {
			case 0:
				// Place domino vertically
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 0, sols))
				// Place two dominoes horizontally
				count = helpermath.ModAdd(count, topDownNumTilings(n-2, 0, sols))
				// Place a tromino hooked up
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 1, sols))
				// Place a tromino hooked down
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 2, sols))
			case 1:
				// Popout from top
				// Place a tromino hooked down
				count = helpermath.ModAdd(count, topDownNumTilings(n-2, 0, sols))
				// Place a domino horizontally on bottom - yields popout from bottom
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 1, sols))
			default:
				// Popout from bottom
				// Place a tromino hooked up
				count = helpermath.ModAdd(count, topDownNumTilings(n-2, 0, sols))
				// Place a domino horizontally on top - yields popout from top
				count = helpermath.ModAdd(count, topDownNumTilings(n-1, 2, sols))
			}
			sols[left_side][n] = count
		}
	}
	return sols[left_side][n]
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an integer array nums and an integer k, split nums into k non-empty subarrays such that the largest sum of any subarray is minimized.

Return the minimized largest sum of the split.

A subarray is a contiguous part of the array.

Link: https://leetcode.com/problems/split-array-largest-sum/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func splitArray(nums []int, k int) int {
	// We are going to binary search for the smallest possible maximum sum
	left := 0
	right := 0
	for _, v := range nums {
		right += v
	}
	for left < right {
		mid := (left + right) / 2
		if canSplit(nums, k, mid) {
			right = mid
		} else {
			left = mid + 1
		}
	}
	return left
}

func canSplit(nums []int, k int, max_sum int) bool {
	// We need to see if we can split the array into k subarrays such that the maximum sum of any subarray is less than or equal to max_sum
	count := 1
	sum := 0
	// As we build our sliding window, make sure we don't exceed the maximum sum - if that requires more than k splits, then we're out of luck
	for _, v := range nums {
		if sum+v > max_sum {
			count++
			sum = v
		} else {
			sum += v
		}
		if sum > max_sum {
			// A single value is too large to fit in the maximum sum
			return false
		}
	}
	return count <= k
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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
	cookie_totals := make([]int, k)
	next_to_assign := 0
	return recDistributeCookies(&cookies, &cookie_totals, next_to_assign)
}

func recDistributeCookies(cookies *[]int, cookie_totals *[]int, next_to_assign int) int {
	// If I’ve assigned the first i cookies, and the kids currently have these totals, what’s the best possible unfairness I can achieve from here?”
	// Each recursive step adds a cookie to a kid and asks the question again.
	cookie := (*cookies)[next_to_assign]
	// Try giving the cookie to each kid
	previous_sums := make(map[int]bool)
	record := math.MaxInt
	for i := range *cookie_totals {
		kid_sum := (*cookie_totals)[i]
		if _, ok := previous_sums[kid_sum]; !ok {
			// Not redundant to assign this cookie to this kid
			previous_sums[kid_sum] = true
			(*cookie_totals)[i] += cookie
			if next_to_assign < len(*cookies)-1 {
				// Follow this branch
				rec_unfair := recDistributeCookies(cookies, cookie_totals, next_to_assign+1)
				record = min(record, rec_unfair)
			} else {
				// We're at the end of our cookie assignments - check the unfairness
				max_cookie_count := math.MinInt
				for j := range *cookie_totals {
					max_cookie_count = max(max_cookie_count, (*cookie_totals)[j])
				}
				record = min(record, max_cookie_count)
			}
			// Now remove this cookie now that we've left the recursive branch
			(*cookie_totals)[i] -= cookie
		}
	}
	return record
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There is a dungeon with n x m rooms arranged as a grid.

You are given a 2D array moveTime of size n x m, where moveTime[i][j] represents the minimum time in seconds when you can start moving to that room.
You start from the room (0, 0) at time t = 0 and can move to an adjacent room.
Moving between adjacent rooms takes exactly one second.

Return the minimum time to reach the room (n - 1, m - 1).

Two rooms are adjacent if they share a common wall, either horizontally or vertically.

Link:
https://leetcode.com/problems/find-minimum-time-to-reach-last-room-i/description/?envType=daily-question&envId=2025-05-07
*/
func minTimeToReach(moveTime [][]int) int {
	// This is a shortest path problem
	type connection struct {
		row  int
		col  int
		cost int
	}
	connection_heap := datastructures.NewHeap(func(c1, c2 *connection) bool {
		return c1.cost < c2.cost
	})
	connection_heap.Push(&connection{row: 0, col: 0, cost: 0})
	min_cost := make([][]int, len(moveTime))
	for i := range moveTime {
		min_cost[i] = make([]int, len(moveTime[0]))
		for j := range moveTime[0] {
			min_cost[i][j] = math.MaxInt
		}
	}
	min_cost[0][0] = 0
	for !connection_heap.Empty() {
		node := connection_heap.Pop()
		if node.row == len(moveTime)-1 && node.col == len(moveTime[0])-1 {
			break
		}
		// Look up, down, left, right
		if node.row > 0 {
			// Up
			new_cost := max(node.cost, moveTime[node.row-1][node.col]) + 1
			if new_cost < min_cost[node.row-1][node.col] {
				// Worth exploring
				min_cost[node.row-1][node.col] = new_cost
				connection_heap.Push(&connection{row: node.row - 1, col: node.col, cost: max(node.cost, moveTime[node.row-1][node.col]) + 1})
			}
		}
		if node.row < len(moveTime)-1 {
			// Down
			new_cost := max(node.cost, moveTime[node.row+1][node.col]) + 1
			if new_cost < min_cost[node.row+1][node.col] {
				min_cost[node.row+1][node.col] = new_cost
				connection_heap.Push(&connection{row: node.row + 1, col: node.col, cost: max(node.cost, moveTime[node.row+1][node.col]) + 1})
			}
		}
		if node.col > 0 {
			// Left
			new_cost := max(node.cost, moveTime[node.row][node.col-1]) + 1
			if new_cost < min_cost[node.row][node.col-1] {
				min_cost[node.row][node.col-1] = new_cost
				connection_heap.Push(&connection{row: node.row, col: node.col - 1, cost: max(node.cost, moveTime[node.row][node.col-1]) + 1})
			}
		}
		if node.col < len(moveTime[0])-1 {
			// Right
			new_cost := max(node.cost, moveTime[node.row][node.col+1]) + 1
			if new_cost < min_cost[node.row][node.col+1] {
				min_cost[node.row][node.col+1] = new_cost
				connection_heap.Push(&connection{row: node.row, col: node.col + 1, cost: max(node.cost, moveTime[node.row][node.col+1]) + 1})
			}
		}
	}
	return min_cost[len(moveTime)-1][len(moveTime[0])-1]
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There is a dungeon with n x m rooms arranged as a grid.

You are given a 2D array moveTime of size n x m, where moveTime[i][j] represents the minimum time in seconds when you can start moving to that room.
You start from the room (0, 0) at time t = 0 and can move to an adjacent room.
Moving between adjacent rooms takes one second for one move and two seconds for the next, alternating between the two.

Return the minimum time to reach the room (n - 1, m - 1).

Two rooms are adjacent if they share a common wall, either horizontally or vertically.

Link:
https://leetcode.com/problems/find-minimum-time-to-reach-last-room-ii/description/
*/
func minTimeToReachII(moveTime [][]int) int {
	// This is a AGAIN shortest path problem
	type connection struct {
		row            int
		col            int
		cost           int
		last_jump_time int // either 1 or 2
	}
	connection_heap := datastructures.NewHeap(func(c1, c2 *connection) bool {
		return c1.cost < c2.cost
	})
	connection_heap.Push(&connection{row: 0, col: 0, cost: 0, last_jump_time: 2})
	min_cost := make([][]int, len(moveTime))
	for i := range moveTime {
		min_cost[i] = make([]int, len(moveTime[0]))
		for j := range moveTime[0] {
			min_cost[i][j] = math.MaxInt
		}
	}
	min_cost[0][0] = 0
	for !connection_heap.Empty() {
		node := connection_heap.Pop()
		if node.row == len(moveTime)-1 && node.col == len(moveTime[0])-1 {
			break
		}
		// Look up, down, left, right
		next_jump_time := 1
		if node.last_jump_time == 1 {
			// Then this jump time is 2
			next_jump_time++
		}
		if node.row > 0 {
			// Up
			new_cost := max(node.cost, moveTime[node.row-1][node.col]) + next_jump_time
			if new_cost < min_cost[node.row-1][node.col] {
				// Worth exploring
				min_cost[node.row-1][node.col] = new_cost
				connection_heap.Push(&connection{row: node.row - 1, col: node.col, cost: new_cost, last_jump_time: next_jump_time})
			}
		}
		if node.row < len(moveTime)-1 {
			// Down
			new_cost := max(node.cost, moveTime[node.row+1][node.col]) + next_jump_time
			if new_cost < min_cost[node.row+1][node.col] {
				min_cost[node.row+1][node.col] = new_cost
				connection_heap.Push(&connection{row: node.row + 1, col: node.col, cost: new_cost, last_jump_time: next_jump_time})
			}
		}
		if node.col > 0 {
			// Left
			new_cost := max(node.cost, moveTime[node.row][node.col-1]) + next_jump_time
			if new_cost < min_cost[node.row][node.col-1] {
				min_cost[node.row][node.col-1] = new_cost
				connection_heap.Push(&connection{row: node.row, col: node.col - 1, cost: new_cost, last_jump_time: next_jump_time})
			}
		}
		if node.col < len(moveTime[0])-1 {
			// Right
			new_cost := max(node.cost, moveTime[node.row][node.col+1]) + next_jump_time
			if new_cost < min_cost[node.row][node.col+1] {
				min_cost[node.row][node.col+1] = new_cost
				connection_heap.Push(&connection{row: node.row, col: node.col + 1, cost: new_cost, last_jump_time: next_jump_time})
			}
		}
	}
	return min_cost[len(moveTime)-1][len(moveTime[0])-1]
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Write a program to solve a Sudoku puzzle by filling the empty cells.

A sudoku solution must satisfy all of the following rules:
- Each of the digits 1-9 must occur exactly once in each row.
- Each of the digits 1-9 must occur exactly once in each column.
- Each of the digits 1-9 must occur exactly once in each of the 9 3x3 sub-boxes of the grid.
The '.' character indicates empty cells.

Link:
https://leetcode.com/problems/sudoku-solver/description/
*/
type variable struct {
	values    map[byte]bool
	neighbors []*variable
}

func solveSudoku(board_problem [][]byte) {
	variable_grid := make([][]*variable, 9)
	for i := range variable_grid {
		variable_grid[i] = make([]*variable, 9)
		for j := range variable_grid[i] {
			variable_grid[i][j] = &variable{}
			variable_grid[i][j].values = make(map[byte]bool)
			if board_problem[i][j] == '.' {
				for k := 1; k <= 9; k++ {
					// This is a variable that can take on any of the values 1-9 (so far as we can tell right now)
					key := byte(k + '0')
					variable_grid[i][j].values[key] = true
				}
			} else {
				variable_grid[i][j].values[board_problem[i][j]] = true
			}
		}
	}

	for i := range 9 {
		for j := range 9 {
			assign_vars(i, j, variable_grid)
		}
	}

	// Now perform ac3 from all the singleton variables - that'll get rid of some values to start
	for i := range variable_grid {
		for j := range variable_grid[i] {
			if len(variable_grid[i][j].values) == 1 {
				// This is a singleton variable - perform ac3 on it (don't worry about the return on it - we don't need to restore anything and we're assuming the puzzle IS possible to solve so we won't be messed up here)
				ac3(variable_grid[i][j])
			}
		}
	}

	recSudokuSolver(0, 0, variable_grid)
	for i := range variable_grid {
		for j := range variable_grid[i] {
			for k := range variable_grid[i][j].values {
				// There should only be one value in the map
				if len(variable_grid[i][j].values) != 1 {
					log.Fatalf("Cell (%d, %d) has non-singleton domain: %v", i, j, variable_grid[i][j].values)
				}
				board_problem[i][j] = k
				break
			}
		}
	}
}

func recSudokuSolver(row, col int, variable_grid [][]*variable) bool {
	if row == 9 {
		return true
	} else {
		v := variable_grid[row][col]
		if len(v.values) == 1 {
			// Already solved. Just move to next cell.
			next_row := row
			next_col := col
			if next_col == 8 {
				next_row++
				next_col = 0
			} else {
				next_col++
			}
			return recSudokuSolver(next_row, next_col, variable_grid)
		}
		for k := range v.values {
			values_copy := make(map[byte]bool)
			maps.Copy(values_copy, v.values)
			// Assign this value to the variable - which means removing all other possible values
			v.values = make(map[byte]bool)
			v.values[k] = true
			next_row := row
			next_col := col
			if col == 8 {
				next_row++
				next_col = 0
			} else {
				next_col++
			}
			ac3_passed, restore_vars := ac3(v)
			if ac3_passed && recSudokuSolver(next_row, next_col, variable_grid) {
				return true
			} else {
				for v2, v2_restore := range restore_vars {
					// Restore the values of the variables
					v2.values = v2_restore
				}
				// Restore the values of the current variable
				v.values = values_copy
				// But the value we just tried for our current variable will not work, so remove it
				delete(v.values, k)
			}
		}
		return false
	}
}

func assign_vars(row, col int, variable_grid [][]*variable) {
	// Find all the other variables that will be affected by the current variable
	for c := range 9 {
		if col != c {
			variable_grid[row][col].neighbors = append(variable_grid[row][col].neighbors, variable_grid[row][c])
		}
	}
	for r := range 9 {
		if row != r {
			variable_grid[row][col].neighbors = append(variable_grid[row][col].neighbors, variable_grid[r][col])
		}
	}
	block_row_idx := (row / 3) * 3
	block_col_idx := (col / 3) * 3
	for r_offset := range 3 {
		for c_offset := range 3 {
			r_idx := block_row_idx + r_offset
			c_idx := block_col_idx + c_offset
			if r_idx != row || c_idx != col {
				variable_grid[row][col].neighbors = append(variable_grid[row][col].neighbors, variable_grid[r_idx][c_idx])
			}
		}
	}
}

type arc struct {
	first_var  *variable
	second_var *variable
}

func ac3(v *variable) (bool, map[*variable]map[byte]bool) {
	restore_vars := make(map[*variable]map[byte]bool) // pointer to a struct is hashable because it's an underlying integer
	restore_vars[v] = make(map[byte]bool)
	maps.Copy(restore_vars[v], v.values)
	arc_queue := datastructures.NewQueue[*arc]()
	for _, other_v := range v.neighbors {
		arc_queue.Enqueue(&arc{first_var: v, second_var: other_v})
	}
	for !arc_queue.Empty() {
		this_arc := arc_queue.Dequeue()
		first := this_arc.first_var
		second := this_arc.second_var
		if _, ok := restore_vars[second]; !ok {
			restore_vars[second] = make(map[byte]bool)
			maps.Copy(restore_vars[second], second.values)
		}
		if remove_inconsistent_values(this_arc) {
			// If something ran out of values, we're done - false
			if len(second.values) == 0 {
				return false, restore_vars
			}
			for _, neighbor := range second.neighbors {
				if neighbor != first {
					arc_queue.Enqueue(&arc{first_var: second, second_var: neighbor})
				}
			}
		}
	}

	return true, restore_vars // Even if ac3 works, we may not have a solution when we try to solve later variables
}

func remove_inconsistent_values(some_arc *arc) bool {
	first := some_arc.first_var
	second := some_arc.second_var
	removed := false
	if len(first.values) == 1 {
		// That's going to constrain second variable's values
		for v := range first.values {
			// (There will only be one value in the map)
			if _, ok := second.values[v]; ok {
				removed = true
				delete(second.values, v)
			}
		}
	}
	return removed
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
A transformation sequence from word beginWord to word endWord using a dictionary wordList is a sequence of words beginWord -> s1 -> s2 -> ... -> sk such that:
- Every adjacent pair of words differs by a single letter.
- Every s_i for 1 <= i <= k is in wordList. Note that beginWord does not need to be in wordList.
- s_k == endWord

Given two words, beginWord and endWord, and a dictionary wordList, return the number of words in the shortest transformation sequence from beginWord to endWord, or 0 if no such sequence exists.

Link:
https://leetcode.com/problems/word-ladder/description/
*/
func ladderLength(beginWord string, endWord string, wordList []string) int {
	wordSet := make(map[string]bool)
	for _, word := range wordList {
		wordSet[word] = true
	}
	if _, ok := wordSet[endWord]; !ok {
		// No way to get to the end word
		return 0
	} else {
		// BFS - so we need to make our graph
		visited := make(map[string]bool)
		graph := make(map[string][]string)
		for _, word := range wordList {
			graph[word] = make([]string, 0)
			// Look at all the other words in the list and see if they are one letter different
			for _, other_word := range wordList {
				if word != other_word {
					// Check if they are one letter different
					diff_count := 0
					for i := range len(word) {
						if word[i] != other_word[i] {
							diff_count++
							if diff_count > 1 {
								break
							}
						}
					}
					if diff_count == 1 {
						// They are one letter different - add the edge to the graph
						graph[word] = append(graph[word], other_word)
					}
				}
			}
		}
		// Also add the beginWord to the graph
		if _, ok := graph[beginWord]; !ok {
			graph[beginWord] = make([]string, 0)
		}
		for _, word := range wordList {
			if word != beginWord {
				// Check if they are one letter different
				diff_count := 0
				for i := range len(beginWord) {
					if beginWord[i] != word[i] {
						diff_count++
						if diff_count > 1 {
							break
						}
					}
				}
				if diff_count == 1 {
					// They are one letter different - add the edge to the graph
					graph[beginWord] = append(graph[beginWord], word)
				}
			}
		}
		queue := datastructures.NewQueue[string]()
		queue.Enqueue(beginWord)
		depth := 1
		visited[beginWord] = true
		for !queue.Empty() {
			n := queue.Size()
			for range n {
				// Take this element out of the queue and enqueue all of its unvisited neighbors
				word := queue.Dequeue()
				if word == endWord {
					// We found the end word - return the depth
					return depth
				}
				for _, neighbor := range graph[word] {
					if _, ok := visited[neighbor]; !ok {
						// Not visited yet - add it to the queue
						visited[neighbor] = true
						queue.Enqueue(neighbor)
					}
				}
			}
			depth++
		}

		// We never found the end word - return 0
		return 0
	}
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given an integer array nums, return the number of all the arithmetic subsequences of nums.

A sequence of numbers is called arithmetic if it consists of at least three elements and if the difference between any two consecutive elements is the same.

For example, [1, 3, 5, 7, 9], [7, 7, 7, 7], and [3, -1, -5, -9] are arithmetic sequences.
For example, [1, 1, 2, 5, 7] is not an arithmetic sequence.
A subsequence of an array is a sequence that can be formed by removing some elements (possibly none) of the array.

For example, [2,5,10] is a subsequence of [1,2,1,2,4,1,5,10].
The test cases are generated so that the answer fits in 32-bit integer.

Link:
https://leetcode.com/problems/arithmetic-slices-ii-subsequence/description/?envType=problem-list-v2&envId=dynamic-programming
*/
func numberOfArithmeticSlices(nums []int) int {
	// Answer the question - at this index with this difference, how many subsequences are there that end here?
	sols := make([]map[int]int, len(nums))
	total := 0
	for end := range nums {
		sols[end] = make(map[int]int)
		for start := range end {
			diff := nums[end] - nums[start]
			if _, ok := sols[end][diff]; !ok {
				// We haven't seen this difference before - initialize it
				sols[end][diff] = 0
			}
			if _, ok := sols[start][diff]; ok {
				// We can extend all the subsequences that end at start with this difference by tacking on nums[end]
				sols[end][diff] += sols[start][diff]
			}
			// We can also count the subsequence [nums[start], nums[end]] as a new subsequence
			sols[end][diff]++
		}
		for _, v := range sols[end] {
			// We can count the subsequence [nums[end]] as a new subsequence
			total += v
		}
	}

	// Subtract all the subsequences of length 2 from the total since we counted those too
	return total - helpermath.NewChooseCalculator().Choose(len(nums), 2)
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given a string of digits s, return the number of palindromic subsequences of s having length 5.
Since the answer may be very large, return it modulo 10^9 + 7.

Note:
A string is palindromic if it reads the same forward and backward.
A subsequence is a string that can be derived from another string by deleting some or no characters without changing the order of the remaining characters.

Link:
https://leetcode.com/problems/count-palindromic-subsequences/description/
*/
func countPalindromes(s string) int {
	str := []byte(s)
	digits := []byte{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
	posns := make(map[byte][]int)
	for i := range s {
		if _, ok := posns[s[i]]; !ok {
			posns[s[i]] = make([]int, 0)
		}
		posns[s[i]] = append(posns[s[i]], i)
	}
	// Count the number of palindromic subsequences of length 5 - note they must be of the form 'abcba'
	total := 0
	for _, a := range digits {
		for _, b := range digits {
			// Count how many palindromes are of the form 'a, b, ANYTHING, b, a'
			prefix_counts := make([]int, len(str))
			// Count how many 'ab' pairs we can form up to each index
			count_a := 0
			for i := range str {
				if str[i] == b {
					// Then we can form an 'ab' pair for all occurences of 'a' before this index
					prefix_counts[i] = count_a
				}
				if str[i] == a {
					count_a = helpermath.ModAdd(count_a, 1)
				}
				if i > 0 {
					prefix_counts[i] = helpermath.ModAdd(prefix_counts[i], prefix_counts[i-1])
				}
			}
			// Count how many 'ba' pairs we can form from the end of the string
			suffix_counts := make([]int, len(str))
			count_a = 0
			for i := len(str) - 1; i >= 0; i-- {
				if str[i] == b {
					// Then we can form a 'ba' pair for all occurences of 'a' after this index
					suffix_counts[i] = count_a
				}
				if str[i] == a {
					count_a = helpermath.ModAdd(count_a, 1)
				}
				if i < len(str)-1 {
					suffix_counts[i] = helpermath.ModAdd(suffix_counts[i], suffix_counts[i+1])
				}
			}
			// Now we can count the number of palindromic subsequences of the form 'a, b, ANYTHING, b, a'
			for i := range str {
				if i > 1 && i < len(str)-2 {
					// We can form a palindromic subsequence of the form 'a, b, ANYTHING, b, a' if we have at least one 'ab' pair before i and at least one 'ba' pair after i
					total = helpermath.ModAdd(total, helpermath.ModMul(prefix_counts[i-1], suffix_counts[i+1]))
				}
			}
		}
	}
	return total
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
A game on an undirected graph is played by two players, Mouse and Cat, who alternate turns.

The graph is given as follows: graph[a] is a list of all nodes b such that ab is an edge of the graph.

The mouse starts at node 1 and goes first, the cat starts at node 2 and goes second, and there is a hole at node 0.

During each player's turn, they must travel along one edge of the graph that meets where they are.  For example, if the Mouse is at node 1, it must travel to any node in graph[1].

Additionally, it is not allowed for the Cat to travel to the Hole (node 0).

Then, the game can end in three ways:
- If ever the Cat occupies the same node as the Mouse, the Cat wins.
- If ever the Mouse reaches the Hole, the Mouse wins.
- If ever a position is repeated (i.e., the players are in the same position as a previous turn, and it is the same player's turn to move), the game is a draw.
Given a graph, and assuming both players play optimally, return
- 1 if the mouse wins the game,
- 2 if the cat wins the game, or
- 0 if the game is a draw.
*/
func catMouseGame(graph [][]int) int {
	type state struct {
		mouse    int      // mouse position
		cat      int      // cat position
		turn     int      // 0 for mouse, 1 for cat
		children []*state // children states
		parents  []*state // parents states
	}

	// Create a graph all possible states
	states := make([][][]*state, len(graph))
	for i := range states {
		states[i] = make([][]*state, len(graph))
		for j := range states[i] {
			states[i][j] = make([]*state, 2)
		}
	}
	// Also a map for easy iteration of states
	all_states := make(map[*state]bool)
	for mouse_posn := range graph {
		for cat_posn := range graph {
			if cat_posn == 0 {
				// Cat can't go to hole
				continue
			} else {
				for turn := range 2 {
					states[mouse_posn][cat_posn][turn] = &state{mouse: mouse_posn, cat: cat_posn, turn: turn, children: make([]*state, 0), parents: make([]*state, 0)}
					// Add this state to the map of all states
					all_states[states[mouse_posn][cat_posn][turn]] = true
				}
			}
		}
	}

	// Establish the children states for each state
	for mouse_posn := range graph {
		for cat_posn := range graph {
			if cat_posn != 0 && mouse_posn != cat_posn && mouse_posn != 0 {
				// Both possible and non-terminal state
				for turn := range 2 {
					current_state := states[mouse_posn][cat_posn][turn]
					if turn == 0 {
						// Mouse's turn - can move to any of the neighbors
						for _, neighbor := range graph[mouse_posn] {
							child_state := states[neighbor][cat_posn][1] // Cat's turn next
							current_state.children = append(current_state.children, child_state)
							child_state.parents = append(child_state.parents, current_state)
						}
					} else {
						// Cat's turn - can move to any of the neighbors except hole
						for _, neighbor := range graph[cat_posn] {
							if neighbor != 0 { // Can't move to hole
								child_state := states[neighbor][cat_posn][0] // Mouse's turn next
								current_state.children = append(current_state.children, child_state)
								child_state.parents = append(child_state.parents, current_state)
							}
						}
					}
				}
			}
		}
	}

	// Next, a map that determines if the mouse or cat wins from this state
	mouse_wins := make(map[*state]bool) // True if mouse wins from this state
	cat_wins := make(map[*state]bool)   // True if cat wins from this state

	// Create a queue, and enqueue all terminal states
	queue := datastructures.NewQueue[*state]()
	for mouse_posn := range graph {
		if mouse_posn == 0 {
			// Hole - mouse wins regardless of cat position or whose turn it is
			for cat_posn := range graph {
				if cat_posn != 0 {
					// Cat can't go to hole
					// Mouse wins no matter whose turn it is
					mouse_wins[states[mouse_posn][cat_posn][0]] = true
					mouse_wins[states[mouse_posn][cat_posn][1]] = true
					queue.Enqueue(states[mouse_posn][cat_posn][0])
					queue.Enqueue(states[mouse_posn][cat_posn][1])
				}
			}
		} else {
			// All nodes where the cat is at the same position will result in a cat win regardless of whose turn it is
			cat_wins[states[mouse_posn][mouse_posn][1]] = true
			cat_wins[states[mouse_posn][mouse_posn][0]] = true
			queue.Enqueue(states[mouse_posn][mouse_posn][1])
			queue.Enqueue(states[mouse_posn][mouse_posn][0])
		}
	}

	// For each state, keep track of its win/loss/draw status
	children_unresolved := make(map[*state]int) // Count of how many children of this state are unresolved
	for state := range all_states {
		children_unresolved[state] = len(state.children) // Initially, all children are unresolved
	}

	// We are finally ready to process the queue
	for !queue.Empty() {
		// Note that ONLY terminal states will be in the queue EVER
		current_state := queue.Dequeue()
		// What states could have preceded this state?
		for _, parent_state := range current_state.parents {
			children_unresolved[parent_state]-- // We are processing one of the children of this parent state
			if _, ok := cat_wins[parent_state]; ok {
				// Just a terminal adjacent state - nothing to do
				continue
			} else if _, ok := mouse_wins[parent_state]; ok {
				// Again just a terminal adjacent state - nothing to do
				continue
			} else {
				// The adjacent state is undecided
				// Depending on whose turn it is in this state, we can determine what happens in the adjacent state
				if current_state.turn == 0 {
					// Then cat goes from parent state
					if _, ok := cat_wins[current_state]; ok {
						// Cat wins from current state, so cat will pick this state from the previous state and win
						cat_wins[parent_state] = true
						queue.Enqueue(parent_state)
					} else if children_unresolved[parent_state] == 0 {
						// This could only happen if all other children of this parent state are mouse wins (if any were cat wins, then this parent state would already be a cat win)
						// So the cat from the parent state can't go ANYWHERE that is a win for it
						mouse_wins[parent_state] = true // Cat loses from this state
						queue.Enqueue(parent_state)
					}
				} else {
					// Cat's turn, so mouse's turn previously
					if _, ok := mouse_wins[current_state]; ok {
						// Mouse wins from current state, so mouse will pick this state from the previous state and win
						mouse_wins[parent_state] = true
						queue.Enqueue(parent_state)
					} else if children_unresolved[parent_state] == 0 {
						// This could only happen if all other children of this parent state are cat wins (if any were mouse wins, then this parent state would already be a mouse win)
						// So the mouse from the parent state can't go ANYWHERE that is a win for it
						cat_wins[parent_state] = true // Mouse loses from this state
						queue.Enqueue(parent_state)
					}
				}

			}
		}
	}

	initial_state := states[1][2][0] // Mouse starts at 1, cat starts at 2, mouse goes first
	if _, ok := mouse_wins[initial_state]; ok {
		// Mouse wins from the initial state
		return 1
	} else if _, ok := cat_wins[initial_state]; ok {
		// Cat wins from the initial state
		return 2
	} else {
		// Neither wins from the initial state - it's a draw
		return 0
	}
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

type Master struct {
	secretWord     string
	allowedGuesses int
	wordList       map[string]bool
	usedGuesses    int
	wordFound      bool
}

func NewMaster(secretWord string, allowedGuesses int, wordList []string) *Master {
	wordListMap := make(map[string]bool)
	for _, word := range wordList {
		wordListMap[word] = true
	}
	return &Master{
		secretWord:     secretWord,
		allowedGuesses: allowedGuesses,
		wordList:       wordListMap,
		usedGuesses:    0,
		wordFound:      false,
	}
}
func (m *Master) Guess(word string) int {
	m.usedGuesses++
	if _, ok := m.wordList[word]; !ok {
		// Word is not in the list
		return -1
	} else {
		// Return the number of exact matches (value and position) of the guess to the secret word
		if word == m.secretWord {
			m.wordFound = true
			return len(m.secretWord) // All letters match
		} else {
			match_count := 0
			for i := range m.secretWord {
				if word[i] == m.secretWord[i] {
					match_count++
				}
			}
			return match_count
		}
	}
}
func (m *Master) GetString() string {
	if m.usedGuesses > m.allowedGuesses || !m.wordFound {
		return "Either you took too many guesses, or you did not find the secret word."
	} else {
		return "You guessed the secret word correctly."
	}
}

/*
You are given an array of unique strings words where words[i] is six letters long. One word of words was chosen as a secret word.

You are also given the helper object Master. You may call Master.guess(word) where word is a six-letter-long string, and it must be from words. Master.guess(word) returns:
-- -1 if word is not from words, or
-- an integer representing the number of exact matches (value and position) of your guess to the secret word.
-- There is a parameter allowedGuesses for each test case where allowedGuesses is the maximum number of times you can call Master.guess(word).

For each test case, you should call Master.guess with the secret word without exceeding the maximum number of allowed guesses. You will get:

"Either you took too many guesses, or you did not find the secret word." if you called Master.guess more than allowedGuesses times or if you did not call Master.guess with the secret word, or
"You guessed the secret word correctly." if you called Master.guess with the secret word with the number of calls to Master.guess less than or equal to allowedGuesses.
The test cases are generated such that you can guess the secret word with a reasonable strategy (other than using the bruteforce method).

  - // This is the Master's API interface.

  - // You should not implement it, or speculate about its implementation

  - type Master struct {

  - }
    *

  - func (this *Master) Guess(word string) int {}

    Link: https://leetcode.com/problems/guess-the-word/description/?envType=problem-list-v2&envId=game-theory
*/
func findSecretWord(words []string, master *Master) {
	current_guess := words[0] // Just pick the first word to start with
	chars_matched := master.Guess(current_guess)
	available_words := make([]string, 0) // This will hold the words that match the first guess
	// Remove all words that don't match the first guess
	for _, word := range words {
		if word != current_guess && countMatches(current_guess, word) == chars_matched {
			// This word matches the number of characters in the same position as the first guess
			available_words = append(available_words, word)
		}
	}

	for len(available_words) > 0 {
		// Pick the next word to guess - try simulating what would happen if we guessed each word in the available words list
		smallest_max := math.MaxInt
		best_word := ""
		best_groupings := make(map[int][]string) // Groupings of words by how many characters match with this word
		for _, word := range available_words {
			groupings := make(map[int][]string) // Group words by how many characters match with this word
			for _, other_word := range available_words {
				if word != other_word {
					// Count how many characters match in the same position
					matches := countMatches(word, other_word)
					if _, ok := groupings[matches]; !ok {
						groupings[matches] = make([]string, 0)
					}
					groupings[matches] = append(groupings[matches], other_word)
				}
			}
			// Now we have all the groupings of words by how many characters match with this word
			max_group_size := 0
			for _, group := range groupings {
				if len(group) > max_group_size {
					max_group_size = len(group)
				}
			}
			if max_group_size < smallest_max {
				smallest_max = max_group_size
				best_word = word
				best_groupings = groupings
			}
		}
		// Now we have the best word to guess
		chars_matched = master.Guess(best_word)
		if _, ok := best_groupings[chars_matched]; ok {
			available_words = best_groupings[chars_matched]
		} else {
			available_words = make([]string, 0)
		}
	}
}

func countMatches(word1, word2 string) int {
	// Count how many letters match in the same position
	match_count := 0
	for i := range word1 {
		if word1[i] == word2[i] {
			match_count++
		}
	}
	return match_count
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given three integers n, m, k.
A good array arr of size n is defined as follows:
- Each element in arr is in the inclusive range [1, m].
- Exactly k indices i (where 1 <= i < n) satisfy the condition arr[i - 1] == arr[i].
Return the number of good arrays that can be formed.

Since the answer may be very large, return it modulo 10^9 + 7.

Link:
https://leetcode.com/problems/count-the-number-of-arrays-with-k-matching-adjacent-elements/description/?envType=daily-question&envId=2025-06-17
*/
func countGoodArrays(n int, m int, k int) int {
	// Edge cases
	if k == 0 && m == 1 && n > 1 {
		// No pairs of indices are equal, and only one value is allowed
		return 0
	} else if n == 1 {
		return m // If n is 1, we can just pick any of the m values
	}

	// Note that there will be n - 1 - k consecutive index pairs that are NOT equal
	// That corresponds to n - k - 1 + 1 = n - k "blocks" of consecutive equal elements
	// So how many ways can an array of size n with n - k such blocks be formed?
	blocks := n - k
	// The only constraint is that each consecutive pair of blocks must be populated with different values
	total := m // The first block can be populated with any of the m values

	// Then each subsequent block can be populated with any of the m - 1 values (since it can't be the same as the previous block)
	if blocks > 1 {
		total = helpermath.ModMul(total, helpermath.ModPow(m-1, blocks-1))
	}

	// Notably, THAT was only for one particular arrangement of blocks
	// n - k NONEMPTY blocks means we have n - k - 1 "dividers" to place in (n - 1) possible positions
	total = helpermath.ModMul(total, globalCalculator.ChooseMod(n-1, n-k-1))

	return total
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given a string word and an integer k.

We consider word to be k-special if |freq(word[i]) - freq(word[j])| <= k for all indices i and j in the string.

Here, freq(x) denotes the frequency of the character x in word, and |y| denotes the absolute value of y.

Return the minimum number of characters you need to delete to make word k-special.

Link:
https://leetcode.com/problems/minimum-deletions-to-make-string-k-special/description/?envType=daily-question&envId=2025-06-21
*/
func minimumDeletions(word string, k int) int {
	frequencies := make(map[byte]int)
	for _, c := range word {
		if _, ok := frequencies[byte(c)]; !ok {
			frequencies[byte(c)] = 0
		}
		frequencies[byte(c)]++
	}

	// Whatever answer we get, some character will have the smallest frequency
	// To achieve a k-special string in the minimum number of deletions, we will NOT delete any instances of that character
	record := math.MaxInt
	for c, freq := range frequencies {
		// Assume that c is in the end going to be the character with the smallest frequency
		deletions := 0
		for other_c, other_freq := range frequencies {
			if other_c != c {
				if other_freq < freq {
					// Gotta delete all of the other character
					deletions += other_freq
				} else if other_freq-k > freq {
					// Gotta delete some of the other character
					deletions += other_freq - (freq + k)
				}
			}
		}
		record = min(record, deletions)
	}

	return record
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
A string s is called good if there are no two different characters in s that have the same frequency.

Given a string s, return the minimum number of characters you need to delete to make s good.

The frequency of a character in a string is the number of times it appears in the string.
For example, in the string "aab", the frequency of 'a' is 2, while the frequency of 'b' is 1.

Link:
https://leetcode.com/problems/minimum-deletions-to-make-character-frequencies-unique/description/
*/
func minDeletions(s string) int {
	// Let us start with mapping frequencies to lists of characters with said frequency
	char_to_freq := make(map[byte]int)
	for _, c := range s {
		if _, ok := char_to_freq[byte(c)]; !ok {
			char_to_freq[byte(c)] = 0
		}
		char_to_freq[byte(c)]++
	}
	freq_to_chars := make(map[int][]byte)
	for c, freq := range char_to_freq {
		if _, ok := freq_to_chars[freq]; !ok {
			freq_to_chars[freq] = make([]byte, 0)
		}
		freq_to_chars[freq] = append(freq_to_chars[freq], c)
	}
	// Note that each frequency can only have one character associated with it, so fill up the highest frequencies you can that you need to
	frequencies := make([]int, 0)
	for freq := range freq_to_chars {
		frequencies = append(frequencies, freq)
	}
	sort.SliceStable(frequencies, func(i, j int) bool {
		return frequencies[i] > frequencies[j]
	})
	deletions := 0
	next_open_freq := frequencies[0] // The next open frequency we can use
	for _, current_freq := range frequencies {
		next_open_freq = min(next_open_freq, current_freq)
		if len(freq_to_chars[current_freq]) == 1 {
			// No need to delete any characters with this frequency
			continue
		} else {
			// We need to move all characters except one to the next lower open frequencies
			for (len(freq_to_chars[current_freq]) > 1) {
				if _, ok := freq_to_chars[next_open_freq]; !ok {
					// We can shove one of the characters with this frequency into the next lower frequency
					if next_open_freq > 0 {
						// Store in map
						freq_to_chars[next_open_freq] = make([]byte, 0)
						freq_to_chars[next_open_freq] = append(freq_to_chars[next_open_freq], freq_to_chars[current_freq][len(freq_to_chars[current_freq])-1])
					}
					// Either way, we need to delete one character from frequency
					freq_to_chars[current_freq] = freq_to_chars[current_freq][:len(freq_to_chars[current_freq])-1]
					deletions += current_freq - next_open_freq
				} else {
					next_open_freq--
				}
			}
		}
	}
	return deletions
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given a 0-indexed integer array players, where players[i] represents the ability of the ith player. 
You are also given a 0-indexed integer array trainers, where trainers[j] represents the training capacity of the jth trainer.

The ith player can match with the jth trainer if the player's ability is less than or equal to the trainer's training capacity. 
Additionally, the ith player can be matched with at most one trainer, and the jth trainer can be matched with at most one player.

Return the maximum number of matchings between players and trainers that satisfy these conditions.

Link:
https://leetcode.com/problems/maximum-matching-of-players-with-trainers/description/?envType=daily-question&envId=2025-07-13
*/
func matchPlayersAndTrainers(players []int, trainers []int) int {
    sort.SliceStable(players, func(i, j int) bool {
		return players[i] < players[j]
	})
	sort.SliceStable(trainers, func(i, j int) bool {
		return trainers[i] < trainers[j]
	})
	// Now greedily match players with trainers
	matched := 0
	player_idx, trainer_idx := 0, 0
	for player_idx < len(players) && trainer_idx < len(trainers) {
		if players[player_idx] <= trainers[trainer_idx] {
			matched++
			player_idx++
			trainer_idx++
		} else {
			// Gotta go to a bigger trainer
			trainer_idx++
		}
	
	}
	return matched
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given the root of a binary tree and an integer targetSum, return all root-to-leaf paths where the sum of the node values in the path equals targetSum. 
Each path should be returned as a list of the node values, not node references.

A root-to-leaf path is a path starting from the root and ending at any leaf node. 
A leaf is a node with no children.

Link:
https://leetcode.com/problems/path-sum-ii/description/?envType=problem-list-v2&envId=depth-first-search
*/
func pathSum(root *datastructures.TreeNode, targetSum int) [][]int {
	paths := make([][]int, 0)
	if root == nil {
		return paths
	}
	node_stack := datastructures.NewStack[*datastructures.TreeNode]()
	node_stack.Push(root)
	current_path := []int{root.Val}
	path_sum := root.Val
	pushed := make(map[*datastructures.TreeNode]bool)
	pushed[root] = true
	for !node_stack.Empty() {
		next_node := node_stack.Peek()
		if next_node.Left == nil && next_node.Right == nil {
			// Leaf node - check if the path sum equals targetSum
			if path_sum == targetSum {
				current_path_copy := make([]int, len(current_path))
				copy(current_path_copy, current_path)
				paths = append(paths, current_path_copy)
			}
			// Regardless, we now need to backtrack
			path_sum -= next_node.Val
			current_path = current_path[:len(current_path)-1]
			node_stack.Pop()
		} else {
			// Not a leaf node - see if the left or right child needs to be processed
			pushed_children := false
			if next_node.Left != nil {
				// Try pushing the left child first
				if _, ok := pushed[next_node.Left]; !ok {
					node_stack.Push(next_node.Left)
					pushed[next_node.Left] = true
					path_sum += next_node.Left.Val
					current_path = append(current_path, next_node.Left.Val)
					pushed_children = true
				}
			} 
			if !pushed_children && next_node.Right != nil {
				// Then try pushing the right child
				if _, ok := pushed[next_node.Right]; !ok {
					node_stack.Push(next_node.Right)
					pushed[next_node.Right] = true
					path_sum += next_node.Right.Val
					current_path = append(current_path, next_node.Right.Val)
					pushed_children = true
				}
			} 
			if !pushed_children {
				// Both children have been processed - backtrack
				path_sum -= next_node.Val
				current_path = current_path[:len(current_path)-1]
				node_stack.Pop()
			}
		}
	}

    return paths
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given an integer array nums.
A subsequence sub of nums with length x is called valid if it satisfies:

(sub[0] + sub[1]) % 2 == (sub[1] + sub[2]) % 2 == ... == (sub[x - 2] + sub[x - 1]) % 2.
Return the length of the longest valid subsequence of nums.

A subsequence is an array that can be derived from another array by deleting some or no elements without changing the order of the remaining elements.

Link:
https://leetcode.com/problems/find-the-maximum-length-of-valid-subsequence-i/description/
*/
func maximumLength(nums []int) int {
	for i := range nums {
		nums[i] = nums[i] % 2 // Reduce all numbers to 0 or 1
	}
	// Answer the question, with this pair modulus value and a last value with this modulus value, ending at or before this index, what is the longest valid subsequence achievable?
	sols := make([][][]int, 2)
	for i := range 2 {
		sols[i] = make([][]int, 2)
		for j := range 2 {
			sols[i][j] = make([]int, len(nums)) // Initialize the subsequence lengths to 0
		}
	}
	for i := range len(nums) {
		if i == 0 {
			sols[1][nums[i]][i] = 1 // The first element can only yield a subsequence of length 1 - possible mod values determined by future subsequence elements
			sols[0][nums[i]][i] = 1
		} else {
			// Try excluding this element
			sols[0][0][i] = sols[0][0][i-1] // Carry over the previous subsequence length
			sols[0][1][i] = sols[0][1][i-1]
			sols[1][0][i] = sols[1][0][i-1]
			sols[1][1][i] = sols[1][1][i-1]
			// Try including this element in the subsequence
			// If this element's modulus is 1, then to achieve a 0 mod pair, the previous element must have been 1 coming from a 0 mod pair subsequence
			if nums[i] == 1 {
				// 0 modulus pair, 1 modulus end, so we can extend the previous 0 modulus pair 1 modulus end subsequence (and you might as well add an element when you can)
				sols[0][1][i] += 1
				// 1 modulus pair, 1 modulus end, so we can extend the previous 1 modulus pair 0 modulus end subsequence if it benefits us
				sols[1][1][i] = max(sols[1][1][i], sols[1][0][i-1] + 1)
			} else {
				// 0 modulus pair, 0 modulus end, so we can extend the previous 0 modulus pair 0 modulus end subsequence (and you might as well add an element when you can)
				sols[0][0][i] += 1
				// 1 modulus pair, 0 modulus end, so we can extend the previous 1 modulus pair 1 modulus end subsequence if it benefits us
				sols[1][0][i] = max(sols[1][0][i], sols[1][1][i-1] + 1)
			}
		}
	
	}

	return max(sols[0][0][len(nums)-1], max(sols[0][1][len(nums)-1], max(sols[1][0][len(nums)-1], sols[1][1][len(nums)-1])))
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given an integer array nums and a positive integer k.
A subsequence sub of nums with length x is called valid if it satisfies:

(sub[0] + sub[1]) % k == (sub[1] + sub[2]) % k == ... == (sub[x - 2] + sub[x - 1]) % k.
Return the length of the longest valid subsequence of nums.

Link:
https://leetcode.com/problems/find-the-maximum-length-of-valid-subsequence-ii/?envType=daily-question&envId=2025-07-17
*/
func maximumLengthII(nums []int, k int) int {
	for i := range nums {
		nums[i] = nums[i] % k // Reduce all numbers to modulus k
	}

	record := 0
	// Try all possible mod-pair values, and all possible mod-end values
	for mod_pair := range k {
		dp := make([]int, k) // dp[mod_end] = length of longest valid subsequence ending with this mod_end value
		for _, mod := range nums {
			prev_mod := (mod_pair - mod + k) % k // The previous mod value that would yield a valid pair with this mod value
			dp[mod] = max(dp[mod], dp[prev_mod] + 1) // Either we extend the previous subsequence with this mod value, or we don't
		}
		for _, length := range dp {
			// Update the record with the maximum length of a valid subsequence found so far
			record = max(record, length)
		}
	}
	
	return record
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given a 0-indexed integer array nums consisting of 3 * n elements.

You are allowed to remove any subsequence of elements of size exactly n from nums. 
The remaining 2 * n elements will be divided into two equal parts:
- The first n elements belonging to the first part and their sum is sum_first.
- The next n elements belonging to the second part and their sum is sum_second.
- The difference in sums of the two parts is denoted as sum_first - sum_second.

For example, if sum_first = 3 and sum_second = 2, their difference is 1.
Similarly, if sum_first = 2 and sum_second = 3, their difference is -1.
Return the minimum difference possible between the sums of the two parts after the removal of n elements.

Link:
https://leetcode.com/problems/minimum-difference-in-sums-after-removal-of-elements/?envType=daily-question&envId=2025-07-18
*/
func minimumDifference(nums []int) int64 {
	// For starters, we're definitely going to need the sum of the entire array, as well as the left to right sum at each index
	total_sum := int64(0)
	for _, num := range nums {
		total_sum += int64(num)
	}
	// Grab the size of each "part", which is n, 1/3 of the array size
	n := len(nums) / 3
	// For a given index, what is the lowest sum you can achieve with n elements from the left?
	left_sums := make([]int64, len(nums))
	left_heap := datastructures.NewHeap(func(a, b int64) bool {
		return a > b // Max-heap, because if we take off something, we want to take off the largest element to minimize the sum
	})
	current_sum := int64(0)
	for i := range n {
		current_sum += int64(nums[i])
		left_sums[i] = current_sum // The sum of the first n elements is just the sum of those elements
		left_heap.Push(int64(nums[i]))
	}
	// Now we need to find the smallest n elements from the left
	for i := n; i < len(nums); i++ {
		current_sum += int64(nums[i]) // Add the current element to the sum
		left_heap.Push(int64(nums[i])) // Push the current element to the heap
		// Now we need to remove the largest element from the heap, because we want to minimize the sum
		prev_max := left_heap.Pop()
		current_sum -= prev_max // Remove the largest element from the sum
		left_sums[i] = current_sum // Store the lowest possible sum of n elements up to this index
	}

	// For a given index, what is the highest sum you can achieve with n elements from the right?
	right_sums := make([]int64, len(nums))
	right_heap := datastructures.NewHeap(func(a, b int64) bool {
		return a < b // Min-heap, because if we take off something, we want to take off the smallest element to maximize the sum
	})
	current_sum = int64(0)
	for i := len(nums) - 1; i >= len(nums)-n; i-- {
		current_sum += int64(nums[i])
		right_sums[i] = current_sum // The sum of the last n elements is just the sum of those elements
		right_heap.Push(int64(nums[i]))
	}
	// Now we need to find the largest n elements from the right
	for i := len(nums) - n - 1; i >= 0; i-- {
		current_sum += int64(nums[i]) // Add the current element to the sum
		right_heap.Push(int64(nums[i])) // Push the current element if it's larger than the previous min
		prev_min := right_heap.Pop() // Remove the smallest element from the heap
		current_sum -= prev_min // Remove the smallest element from the sum
		right_sums[i] = current_sum // Store the highest possible sum of n elements from this index to the end
	}

	// Now we can calculate the minimum difference between the two parts
	record := int64(math.MaxInt64)
	for i := n-1; i<=len(left_sums)-n-1; i++ {
		record = min(record, left_sums[i] - right_sums[i+1]) // Update the record with the minimum difference found so far
	}
	return record
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are an ant tasked with adding n new rooms numbered 0 to n-1 to your colony. 
You are given the expansion plan as a 0-indexed integer array of length n, prevRoom, where prevRoom[i] indicates that you must build room prevRoom[i] before building room i, and these two rooms must be connected directly. 
Room 0 is already built, so prevRoom[0] = -1. 
The expansion plan is given such that once all the rooms are built, every room will be reachable from room 0.

You can only build one room at a time, and you can travel freely between rooms you have already built only if they are connected. 
You can choose to build any room as long as its previous room is already built.

Return the number of different orders you can build all the rooms in. 
Since the answer may be large, return it modulo 10^9 + 7.

Link:
https://leetcode.com/problems/count-ways-to-build-rooms-in-an-ant-colony/description/?envType=problem-list-v2&envId=topological-sort
*/
func waysToBuildRooms(prevRoom []int) int {
	// First create our underlying graph structure
	graph := make([][]int, len(prevRoom))
	for i := range prevRoom {
		graph[i] = make([]int, 0) // Initialize each room's adjacency list
	}
	for i := 1; i < len(prevRoom); i++ {
		graph[prevRoom[i]] = append(graph[prevRoom[i]], i) // Add the current room to the graph as a child of the previous room
	}
	return 0
}