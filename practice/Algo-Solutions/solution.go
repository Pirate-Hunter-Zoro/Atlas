package leetcode

import (
	"leet-code/datastructures"
	"leet-code/helpermath"
	"math"
	"sort"
)

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There is a 50 x 50 chessboard with one knight and some pawns on it. 
You are given two integers kx and ky where (kx, ky) denotes the position of the knight, and a 2D array positions where positions[i] = [xi, yi] denotes the position of the pawns on the chessboard.

Alice and Bob play a turn-based game, where Alice goes first. 
In each player's turn:
- The player selects a pawn that still exists on the board and captures it with the knight in the fewest possible moves. 
  Note that the player can select any pawn, it might not be one that can be captured in the least number of moves.
- In the process of capturing the selected pawn, the knight may pass other pawns without capturing them. 
  Only the selected pawn can be captured in this turn.
- Alice is trying to maximize the sum of the number of moves made by both players until there are no more pawns on the board, whereas Bob tries to minimize them.

Return the maximum total number of moves made during the game that Alice can achieve, assuming both players play optimally.

Note that in one move, a chess knight has eight possible positions it can move to, as illustrated below. 
Each move is two cells in a cardinal direction, then one cell in an orthogonal direction.
*/
func maxMoves(kx int, ky int, positions [][]int) int {
	board_size := 50
	positions = append([][]int{{kx,ky}}, positions...)

	// We need to store the solutions for the minimum number of moves to reach any position from any other
	min_hops_to_reach := make(map[int]map[int]int)

	// Using bit-masking, we will remember the solutions for the minimizer and maximizer given the remaining positions and the position we are at
	solver_sols := make(map[int]map[int]map[bool]int)
	
	initial_bit_mask := (1 << (len(positions)-1)) - 1
	return takePawnsSolver(0, initial_bit_mask, solver_sols, positions, min_hops_to_reach, board_size, true)
}

// Helper function to maximize the number of moves to take all the remaining pawns
func takePawnsSolver(start_pawn_idx int, positions_bit_mask int, solver_sols map[int]map[int]map[bool]int, positions [][]int, min_hops_to_reach map[int]map[int]int, board_size int, maximizer bool) int {
	_, ok := solver_sols[start_pawn_idx]
	if !ok {
		solver_sols[start_pawn_idx] = make(map[int]map[bool]int)
	}
	_, ok = solver_sols[start_pawn_idx][positions_bit_mask]
	if !ok {
		solver_sols[start_pawn_idx][positions_bit_mask] = make(map[bool]int)
	}
	_, ok = solver_sols[start_pawn_idx][positions_bit_mask][maximizer]
	if !ok {
		// Need to solve this problem
		remaining_position_indices := []int{}
		for i:=0; i<len(positions); i++ {
			if (1 << i & positions_bit_mask) > 0 {
				remaining_position_indices = append(remaining_position_indices, len(positions)-1-i)
			}
		}
		if len(remaining_position_indices) == 1 {
			// No choice but to take the remaining pawn
			solver_sols[start_pawn_idx][positions_bit_mask][maximizer] = movesToTake(start_pawn_idx, remaining_position_indices[0], positions, min_hops_to_reach, board_size)
		} else {
			// Try taking every possible first pawn and see what that leaves the minimizer with
			record := 0
			if maximizer {
				record = int(math.MinInt) / 2
			} else {
				record = int(math.MaxInt) / 2
			}
			for _, target_pawn_idx := range(remaining_position_indices) {
				new_bit_mask := positions_bit_mask - (1 << (len(positions)-1-target_pawn_idx))
				if maximizer {
					record = max(record, movesToTake(start_pawn_idx, target_pawn_idx, positions, min_hops_to_reach, board_size) + takePawnsSolver(target_pawn_idx, new_bit_mask, solver_sols, positions, min_hops_to_reach, board_size, !maximizer))
				} else {
					record = min(record, movesToTake(start_pawn_idx, target_pawn_idx, positions, min_hops_to_reach, board_size) + takePawnsSolver(target_pawn_idx, new_bit_mask, solver_sols, positions, min_hops_to_reach, board_size, !maximizer))
				}
			}
			solver_sols[start_pawn_idx][positions_bit_mask][maximizer] = record
		}
	}
	return solver_sols[start_pawn_idx][positions_bit_mask][maximizer]
}

// Helper function to determine the number of moves necessary to take a pawn at a given position from another pawn position
func movesToTake(start_pawn_idx int, target_pawn_idx int, pawns [][]int, min_hops_to_reach map[int]map[int]int, board_size int) int {
	// Make sure the map entries exist both ways
	_, ok := min_hops_to_reach[start_pawn_idx]
	if !ok {
		min_hops_to_reach[start_pawn_idx] = make(map[int]int)
	}
	
	// Now go the other way
	_, ok = min_hops_to_reach[target_pawn_idx]
	if !ok {
		min_hops_to_reach[target_pawn_idx] = make(map[int]int)
	}
	
	_, ok = min_hops_to_reach[start_pawn_idx][target_pawn_idx]
	if !ok {
		_, ok = min_hops_to_reach[target_pawn_idx][start_pawn_idx]
		if ok {
			min_hops_to_reach[start_pawn_idx][target_pawn_idx] = min_hops_to_reach[target_pawn_idx][start_pawn_idx]
		}
	}
	if !ok {
		// Need to solve this problem - use BFS
		// Try all (up to 8) possible moves by the knight and see which one yields the best solution
		knight_x, knight_y := pawns[start_pawn_idx][0], pawns[start_pawn_idx][1]
		pawn_x, pawn_y := pawns[target_pawn_idx][0], pawns[target_pawn_idx][1]
		bfs_queue := datastructures.NewQueue[[]int]()
		bfs_queue.Enqueue([]int{knight_x,knight_y})
		visited := make([][]bool, board_size)
		for i:=0; i<board_size; i++ {
			visited[i] = make([]bool, board_size)
		}
		hops := 0
		found := false
		for !bfs_queue.Empty() {
			n := bfs_queue.Size()
			for i:=0; i<n; i++ {
				next := bfs_queue.Dequeue()
				knight_x, knight_y = next[0], next[1]
				if knight_x == pawn_x && knight_y == pawn_y {
					found = true
					break
				}
				if !visited[knight_x][knight_y] {
					visited[knight_x][knight_y] = true
					if knight_x > 0 && knight_y > 1{
						// Try up two, left one
						new_knight_x := knight_x-1
						new_knight_y := knight_y-2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < board_size-1 && knight_y > 1{
						// Try up two, right one
						new_knight_x := knight_x+1
						new_knight_y := knight_y-2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x > 1 && knight_y > 0{
						// Try up one, left two
						new_knight_x := knight_x-2
						new_knight_y := knight_y-1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < board_size-2 && knight_y > 0 {
						// Try up one, right two
						new_knight_x := knight_x+2
						new_knight_y := knight_y-1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x > 0 && knight_y < board_size-2 {
						// Try down two, left one
						new_knight_x := knight_x-1
						new_knight_y := knight_y+2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < board_size-2 && knight_y < board_size-2{
						// Try down two, right one
						new_knight_x := knight_x+1
						new_knight_y := knight_y+2
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x > 1 && knight_y < board_size-1 {
						// Try down one, left two
						new_knight_x := knight_x-2
						new_knight_y := knight_y+1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
					if knight_x < board_size-2 && knight_y < board_size-1 {
						// Try down one, right two
						new_knight_x := knight_x+2
						new_knight_y := knight_y+1
						if !visited[new_knight_x][new_knight_y] {
							bfs_queue.Enqueue([]int{new_knight_x,new_knight_y})
						}
					}
				}
			}
			if found {
				break
			}
			hops++
		}
		min_hops_to_reach[start_pawn_idx][target_pawn_idx] = hops
		min_hops_to_reach[target_pawn_idx][start_pawn_idx] = hops
	} 
	return min_hops_to_reach[start_pawn_idx][target_pawn_idx]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given an array prerequisites where prerequisites[i] = [ai, bi] indicates that you must take course bi first if you want to take course ai.

For example, the pair [0, 1], indicates that to take course 0 you have to first take course 1.
Return true if you can finish all courses. Otherwise, return false.
*/
func canFinish(numCourses int, prerequisites [][]int) bool {
    in_degree := make([]int, numCourses)
	nodes_needed := make([][]int, numCourses) // jagged array
	for i:=0; i<numCourses; i++ {
		nodes_needed[i] = []int{}
	}
	for _, preq := range(prerequisites) {
		need := preq[0]
		needed := preq[1]
		in_degree[needed]++
		nodes_needed[need] = append(nodes_needed[need], needed)
	}

	count_in_degree_0 := 0
	for i := 0; i<numCourses; i++ {
		if in_degree[i] == 0 {
			count_in_degree_0++
		}
	}

	node_queue := datastructures.NewQueue[int]()
	for i, v := range(in_degree) {
		if v == 0 {
			node_queue.Enqueue(i)
		}
	}

	for !node_queue.Empty() {
		next := node_queue.Dequeue()
		for _, neighbor := range(nodes_needed[next]) {
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
*/
func isMatch(s string, p string) bool {
	// Get a couple of edge cases out of the way first...
	if len(p) == 0 {
		return len(s) == 0
	} else if len(s) == 0 {
		for i:=0; i<len(p); i++ {
			if p[i] != '*' {
				return false
			}
		}
		return true
	}

    sols := make([][]bool, len(s)+1)
	for i:=0; i<=len(s); i++ {
		sols[i] = make([]bool, len(p)+1)
	}

	// Empty string matches empty string
	sols[0][0] = true

	// Across the top row - pertains to only matching the empty string with increasing substring lengths of the pattern
	for i:=1; i<len(p); i++ {
		p_idx := i-1
		sols[0][i] = (p[p_idx] == '*' && sols[0][i-1])
	}
	// The left column is all false by default - which it should be except for the 0-0 cell - an empty pattern cannot match a non-empty string

	// Bottom up solution to solve this problem - top to bottom, left to right
	for i:=1; i<=len(s); i++ {
		for j:=1; j<=len(p); j++ {
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

	for j:=0; j<l; j++ {
		i:=j
		last_start := i
		words_seen := 0
		current_seen := make(map[string][]int)
		for i<=len(s)-l {
			word := s[i:i+l]
			count_needed, ok := word_counts[word]
			if !ok {
				// Not part of words at all - we must start over
				i+=l
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
									left = mid+1
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
				first_word := s[last_start:last_start+l]
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
			idx := int(math.Abs(float64(v)))-1
			nums[idx] = -int(math.Abs(float64(nums[idx])))
		}
		// Now go through the list again - the first index that is not negative corresponds with the lowest missing positive value
		for i := 0; i<len(nums); i++ {
			if nums[i] > 0 {
				// Never seen
				return i+1
			}
		}
		// Only remaining possibility
		return n+1
	}
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
You are given an array of k linked-lists lists, each linked-list is sorted in ascending order.

Merge all the linked-lists into one sorted linked-list and return it.
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
		Val: node_heap.Peek().Val,
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
	for i:=range len(s) {
		char := s[i]
		if char == ')' {
			if !char_idx_stack.Empty() && char_idx_stack.Peek().char == '(' {
				// preceded by a '('
				prev_idx := char_idx_stack.Pop().posn
				if len(stretches) > 0 {
					j := len(stretches) - 1
					prev_stretch := stretches[j]
					for j>=0 && prev_stretch[0] > prev_idx && prev_stretch[1] < i {
						// wraps around the most recent valid substring of parentheses
						j--
						if j >= 0 {
							prev_stretch = stretches[j]
						}
					}
					if j < len(stretches)-1 {
						stretches[j+1] = []int{prev_idx,i}
						stretches = stretches[:j+2]
					} else {
						// no previous wraparounds
						stretches = append(stretches, []int{prev_idx,i})
					}
				} else {
					stretches = append(stretches, []int{prev_idx,i})
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
			for split:=range(len(l)-1) {
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
*/
func numDistinct(s string, t string) int {
	// Answer the question - how many different subsequences of s[:i+1] can create t[:j+1]?
    num_distinct := make([][]int, len(s))
	for i:=range(len(s)) {
		num_distinct[i] = make([]int, len(t))
		for j:=range(min(i+1,len(t))){
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
			if s_idx == 0 && s[s_idx]==t[t_idx] {
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
*/
func maxStudents(seats [][]byte) int {
	// From the hints - run a bit mask depending on the previous row of seats
	// For each row, we need a bit mask corresponding to the previous row of seats taken
	// Answer the question - on this row, for this bit mask, what is the maximum number of students that can be sat?
	sols := make([]map[int]int, len(seats))
	for i:=0; i<len(seats); i++ {
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
	for i:=1; i<len(sols); i++ {
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
				sols[i][bit_mask] = max(sols[i][bit_mask], num_sitting + sols[i-1][prev_bit_mask])
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
		available[0] = [][]int{{seat_posns[0]},{}}
		if len(seat_posns) > 1 {
			if seat_posns[1] == seat_posns[0] + 1 {
				// First two seats consecutive
				available[1] = [][]int{{seat_posns[0]},{seat_posns[1]},{}}
			} else {
				// First two seats not consecutive so can go together
				available[1] = [][]int{{seat_posns[0]},{seat_posns[1]},{},{seat_posns[0],seat_posns[1]}}
			}
			for i := range(len(seat_posns)-2) {
				j := i + 2
				posn := seat_posns[j]
				prev_posn := seat_posns[j-1]
				if posn == prev_posn + 1 {
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
		mask_counts = append(mask_counts, []int{bit_mask,len(set)})
	}

	return mask_counts
}

func filterUnavailableBitMasks(num_seats int, bit_mask int, prev_bit_masks []int) []int {
	// Helper method to remove incompatible previous bit masks from the above row given our current row's bit mask
	available := []int{}
	unavailable_spots := []int{}
	for i:=range(num_seats) {
		if ((1 << i) & bit_mask > 0) {
			// This seat is included in the current row bit mask
			if i > 0 {
				unavailable_spots = append(unavailable_spots, i-1)
			}
			if i < num_seats - 1 {
				unavailable_spots = append(unavailable_spots, i+1)
			}
		}
	}
	for _, prev_mask := range prev_bit_masks {
		for _, unavailable_posn := range unavailable_spots {
			if (prev_mask & (1 << unavailable_posn) > 0) {
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
*/
func connectTwoGroups(cost [][]int) int {
	// Inspiration: https://leetcode.com/problems/minimum-cost-to-connect-two-groups-of-points/solutions/5854369/beats-100-on-runtime-and-memory-explained/
    
	// First find the minimum cost for each node in the right to connect to any node in the left
	n_left := len(cost)
	n_right := len(cost[0])
	min_cost_connect := make([]int, n_right)
	for i:=range n_right {
		min_cost_connect[i] = math.MaxInt
		for j:=range n_left {
			min_cost_connect[i] = min(min_cost_connect[i], cost[j][i])
		}
	}

	// Now we are ready to answer the question, given left nodes 1 through 'k' have been connected, and bit mask 'b' of the right nodes have been connected, what is the minimum cost to complete our connections?
	sols := make([][]int, n_left+1)
	for i:=range n_left+1 {
		sols[i] = make([]int, 1<<n_right)
		for j:=range 1<<n_right {
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
			for i:=range n_right {
				if (1 << i) & bit_mask_right == 0 {
					// Node i on the right needs to be connected
					total_cost += min_cost_connect[i]
				}
			}
			sols[num_left_connected][bit_mask_right] = total_cost
		} else {
			// Try connecting the next left node with any node in the right
			total_cost := math.MaxInt
			for i:=range n_right {
				// Try connecting the next left node with Node i on the right
				new_bit_mask := bit_mask_right | (1 << i)
				total_cost = min(total_cost, cost[num_left_connected][i] + recMinConnectTwoGroups(num_left_connected+1, new_bit_mask, sols, min_cost_connect, cost, n_left, n_right))
			}
			sols[num_left_connected][bit_mask_right] = total_cost
		}
	}
	return sols[num_left_connected][bit_mask_right]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
Given a string s, partition s such that every substring of the partition is a palindrome.

Return the minimum cuts needed for a palindrome partitioning of s.

Inspiration: https://leetcode.com/problems/palindrome-partitioning-ii/solutions/42213/easiest-java-dp-solution-97-36/
*/
func minCut(s string) int {
	// Denote min_cuts[i] as the minimum number of cuts needed to partition s[0:i+1] into a palindrome
	min_cuts := make([]int, len(s))
	for i:=range len(s) {
		// This is the HIGHEST possible number of cuts we could possibly need
		min_cuts[i] = i
	}
	is_palindrome := make(map[int]map[int]bool)
	for i:=1; i<len(s); i++ {
		for j:=0; j<=i; j++ {
			if topDownIsPalindrome(s, j, i, is_palindrome) {
				// s[j:i+1] is a palindrome so make that our first partition, then you'd have to partition s[0:j+1]
				if j == 0 {
					// s[0:i+1] is a palindrome so no partitioning necessary
					min_cuts[i] = 0
				} else {
					min_cuts[i] = min(min_cuts[i], 1 + min_cuts[j-1])
				}
			}
		}
	}

	return min_cuts[len(s)-1]
}

func topDownIsPalindrome(s string, start_idx int, end_idx int, is_palindrome map[int]map[int]bool) bool {
	_, ok := is_palindrome[start_idx]
	if !ok {
		is_palindrome[start_idx] = make(map[int]bool)
	}
	_, ok = is_palindrome[start_idx][end_idx]
	if !ok {
		// Need to solve this problem
		if start_idx >= end_idx - 1 {
			// Length 2 or 1 - base case
			is_palindrome[start_idx][end_idx] = s[start_idx] == s[end_idx]
		} else {
			// Check if ends same and recurse
			is_palindrome[start_idx][end_idx] = (s[start_idx] == s[end_idx]) && topDownIsPalindrome(s, start_idx+1, end_idx-1, is_palindrome)
		}
	}

	return is_palindrome[start_idx][end_idx]
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

/*
There are n children standing in a line. 
Each child is assigned a rating value given in the integer array ratings.

You are giving candies to these children subjected to the following requirements:
- Each child must have at least one candy.
- Children with a higher rating get more candies than their neighbors.

Return the minimum number of candies you need to have to distribute the candies to the children.
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
	for i:=range(n) {
		// Store all children - each neighbor of a node is an adjacent child with a lower rating
		graph[i] = []int{}
	}
	for i:=range(n-1) {
		idx := i+1
		left := idx-1
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

