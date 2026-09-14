package maxstudents

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
	numSeats := len(seats[0])

	// Base case is the front row - where the number of students we can sit is simply the number in the row
	maskCounts := findBitMasks(seats[0])
	for _, maskCount := range maskCounts {
		// Bit mask is first element, count is second element
		bitMask := maskCount[0]
		numSitting := maskCount[1]
		sols[0][bitMask] = numSitting
	}

	// Now we go bottom up
	for i := 1; i < len(sols); i++ {
		maskCounts := findBitMasks(seats[i])
		for _, maskCount := range maskCounts {
			bitMask := maskCount[0]
			numSitting := maskCount[1]
			sols[i][bitMask] = 0
			prevBitMasks := []int{}
			for mask := range sols[i-1] {
				prevBitMasks = append(prevBitMasks, mask)
			}
			prevRowBitMasks := filterUnavailableBitMasks(numSeats, bitMask, prevBitMasks)
			for _, prevBitMask := range prevRowBitMasks {
				sols[i][bitMask] = max(sols[i][bitMask], numSitting+sols[i-1][prevBitMask])
			}
		}
	}

	record := 0
	for _, count := range sols[len(sols)-1] {
		record = max(record, count)
	}
	return record
}

func findBitMasks(seatRow []byte) [][]int {
	// Helper method to find all of the available seat bit masks given the row of broken and working seats
	maskCounts := [][]int{}
	seatPosns := []int{}
	for i, b := range seatRow {
		if b == '.' {
			seatPosns = append(seatPosns, i)
		}
	}

	// Note that we cannot pick consecutive seats
	// For each (working) seat, going from left to right, consider taking it, and consider not taking it
	available := make([][][]int, len(seatPosns))
	if len(seatPosns) > 0 {
		available[0] = [][]int{{seatPosns[0]}, {}}
		if len(seatPosns) > 1 {
			if seatPosns[1] == seatPosns[0]+1 {
				// First two seats consecutive
				available[1] = [][]int{{seatPosns[0]}, {seatPosns[1]}, {}}
			} else {
				// First two seats not consecutive so can go together
				available[1] = [][]int{{seatPosns[0]}, {seatPosns[1]}, {}, {seatPosns[0], seatPosns[1]}}
			}
			for i := range len(seatPosns) - 2 {
				j := i + 2
				posn := seatPosns[j]
				prevPosn := seatPosns[j-1]
				if posn == prevPosn+1 {
					// Most previous two seats consecutive
					available[j] = available[j-1] // Don't pick current posn
					// Now add all the options where we do pick the current posn
					for _, pickedSet := range available[j-2] {
						newSet := append(pickedSet, posn)
						available[j] = append(available[j], newSet)
					}
				} else {
					// Most previous two seats not consecutive so can go together
					available[j] = available[j-1] // Again, don't pick current posn
					for _, pickedSet := range available[j-1] {
						newSet := append(pickedSet, posn)
						available[j] = append(available[j], newSet)
					}
				}
			}
		}
	} else {
		// No seats were available
		available = append(available, [][]int{{}})
	}

	// Now look at all the possible seat positions we could pick if we allow all the way up to the last seat on the row
	possibleSets := available[len(available)-1]
	for _, set := range possibleSets {
		bitMask := 0
		for _, posn := range set {
			bitMask += 1 << posn
		}
		maskCounts = append(maskCounts, []int{bitMask, len(set)})
	}

	return maskCounts
}

func filterUnavailableBitMasks(numSeats int, bitMask int, prevBitMasks []int) []int {
	// Helper method to remove incompatible previous bit masks from the above row given our current row's bit mask
	available := []int{}
	unavailableSpots := []int{}
	for i := range numSeats {
		if (1<<i)&bitMask > 0 {
			// This seat is included in the current row bit mask
			if i > 0 {
				unavailableSpots = append(unavailableSpots, i-1)
			}
			if i < numSeats-1 {
				unavailableSpots = append(unavailableSpots, i+1)
			}
		}
	}
	for _, prevMask := range prevBitMasks {
		for _, unavailablePosn := range unavailableSpots {
			if prevMask&(1<<unavailablePosn) > 0 {
				// Need to remove this posn
				prevMask -= 1 << unavailablePosn
			}
		}
		available = append(available, prevMask)
	}

	return available
}
