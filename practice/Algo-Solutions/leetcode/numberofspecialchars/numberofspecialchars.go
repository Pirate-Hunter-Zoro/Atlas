package numberofspecialchars

/*
You are given a string word.
A letter c is called special if it appears both in lowercase and uppercase in word, and every lowercase occurrence of c appears before the first uppercase occurrence of c.

Return the number of special letters in word.

Link:
https://leetcode.com/problems/count-the-number-of-special-characters-ii/description/?envType=daily-question&envId=2026-05-27
*/
func numberOfSpecialChars(word string) int {
	posns := make(map[rune]int)
	special := make(map[rune]bool)
	for i, runeVal := range word {
		if _, ok := posns[runeVal]; !ok {
			posns[runeVal] = i
		}
		v := int(runeVal)
		if v > 90 {
			// Lower case
			upper := rune(v - 32)
			if _, ok := posns[upper]; ok {
				// NOT a special character anymore because this follows an upper case occurrence
				special[runeVal] = false
			}
		} else {
			// Upper case
			lower := rune(v + 32)
			if _, ok := posns[lower]; ok {
				// We have seen the lower case character so unless we know this character can't be special, it now has potential
				if isSpecial, ok := special[lower]; !ok || isSpecial {
					special[lower] = true
				}
			}
		}
	}
	count := 0
	for _, isSpecial := range special {
		if isSpecial {
			count++
		}
	}
	return count
}
