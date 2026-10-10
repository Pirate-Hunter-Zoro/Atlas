package getmaxrepetitions

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
			- We keep track of (index, s1count) in a dictionary to detect cycles.
	*/
	type MatchState struct {
		s1Count int
		s2Count int
	}
	idxMap := make(map[int]MatchState)
	s1MatchCount := 0
	s2LoopCount := 0
	s2Index := 0
	// Keep matching s2 within s1 until we get a repeat instance of s2Index when we're at the start of s1
	for {
		_, ok := idxMap[s2Index]
		// Check for cycle: if we've seen this s2Index before at start of a new s1, we're looping
		if !ok {
			idxMap[s2Index] = MatchState{s1Count: s1MatchCount, s2Count: s2LoopCount}
		} else {
			break
		}
		for i := range len(s1) {
			if s1[i] == s2[s2Index] {
				s2Index++
				if s2Index == len(s2) {
					s2LoopCount++
					s2Index = 0
				}
			}
		}
		s1MatchCount++
	}

	// Now that we've detected our cycle - find out how many times s1 was matched at the start of that cycle, and how many s2 loops it took
	prevS1MatchCount, prevS2LoopCount := idxMap[s2Index].s1Count, idxMap[s2Index].s2Count
	s1CountInCycle := s1MatchCount - prevS1MatchCount
	s2CountInCycle := s2LoopCount - prevS2LoopCount
	s1StartingAtFirstCycle := n1 - prevS1MatchCount
	totalCycles := s1StartingAtFirstCycle / s1CountInCycle
	s2LoopsFromCycles := totalCycles * s2CountInCycle

	// How many s1 are left after all the cycles?
	s1CountAfterCycles := s1StartingAtFirstCycle % s1CountInCycle
	s2CountAfterCycles := 0
	// We need to match that many s1's
	for range s1CountAfterCycles {
		for j := range len(s1) {
			// If we match a character in s1, we need to check if it matches the current character in s2
			if s1[j] == s2[s2Index] {
				s2Index++
				if s2Index == len(s2) {
					s2CountAfterCycles++
					s2Index = 0
				}
			}
		}
	}

	// This is how many times s2 had to be repeated to get to the end of [s1,n1]
	s2Count := s2LoopsFromCycles + s2CountAfterCycles + prevS2LoopCount

	return s2Count / n2 // So that's how many times would could multiply [s2,n2] by and still be a subsequence of [s1,n1]
}
