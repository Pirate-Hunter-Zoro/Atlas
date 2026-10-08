package checkrecord

import (
	"algo-solutions/helpermath"
	"algo-solutions/leetcode"
)

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
The answer may be very large, so return it modulo 10⁹ + 7.

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

func recCheckRecord(numA int, numLeft int, sols []map[int]int) int {
	// See if we have already solved this problem
	if _, ok := sols[numA][numLeft]; !ok {
		// Need to solve this problem
		switch numLeft {
		case 1:
			// We can place a late or a present
			numFirstPossible := 2
			// MAYBE we can place an absent
			if numA > 0 {
				numFirstPossible++
			}
			sols[numA][numLeft] = numFirstPossible
		case 2:
			// LL, LP, PL, PP
			numPossible := 4
			if numA > 0 {
				// AL, AP, PA, LA
				numPossible += 4
			}
			sols[numA][numLeft] = numPossible
		default:
			// Keep a running total
			numPossible := 0

			// Suppose we place a 'L' first - there would be multiple options following
			// Place a 'P' next
			numPossible = helpermath.ModAdd(numPossible, recCheckRecord(numA, numLeft-2, sols), leetcode.MOD)

			// Place an 'L' next, which means we are NOT allowed to place another 'L' after that so place a 'P'
			numPossible = helpermath.ModAdd(numPossible, recCheckRecord(numA, numLeft-3, sols), leetcode.MOD)
			// OR if we have an 'A' left, we could place an 'A' after that second 'L'
			if numA > 0 {
				numPossible = helpermath.ModAdd(numPossible, recCheckRecord(numA-1, numLeft-3, sols), leetcode.MOD)
			}

			// Place an 'A' next after the L - if we can
			if numA > 0 {
				numPossible = helpermath.ModAdd(numPossible, recCheckRecord(numA-1, numLeft-2, sols), leetcode.MOD)
			}

			// Suppose we place a 'P' first - that gives us full freedom with the remaining characters
			numPossible = helpermath.ModAdd(numPossible, recCheckRecord(numA, numLeft-1, sols), leetcode.MOD)

			// Suppose - if we can - we place an 'A' first
			if numA > 0 {
				// That just gives us one less 'A' to use for the next subproblem
				numPossible = helpermath.ModAdd(numPossible, recCheckRecord(numA-1, numLeft-1, sols), leetcode.MOD)
			}

			sols[numA][numLeft] = numPossible
		}
	}
	return sols[numA][numLeft]
}
