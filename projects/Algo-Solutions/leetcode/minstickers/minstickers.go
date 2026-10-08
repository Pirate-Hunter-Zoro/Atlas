package minstickers

import "math"

/*
We are given n different types of stickers.
Each sticker has a lowercase English word on it.

You would like to spell out the given string target by cutting individual letters from your collection of stickers and rearranging them.
You can use each sticker more than once if you want, and you have infinite quantities of each sticker.

Return the minimum number of stickers that you need to spell out target.
If the task is impossible, return -1.

Note: In all test cases, all words were chosen randomly from the 1000 most common US English words, and target was chosen as a concatenation of two random words.

Link:
https://leetcode.com/problems/stickers-to-spell-word/description/?envType=problem-list-v2&envId=bitmask
*/
func minStickers(stickers []string, target string) int {
	targetBytes := []byte(target)
	targetBytesIndices := make(map[byte][]int)
	for i, b := range targetBytes {
		if _, ok := targetBytesIndices[b]; !ok {
			targetBytesIndices[b] = []int{}
		}
		targetBytesIndices[b] = append(targetBytesIndices[b], i)
	}

	// Firstly, see if the problem is possible
	present := make([]bool, len(target))
	for _, sticker := range stickers {
		stickerBytes := []byte(sticker)
		for _, b := range stickerBytes {
			if _, ok := targetBytesIndices[b]; ok {
				for _, j := range targetBytesIndices[b] {
					present[j] = true
				}
			}
		}
	}
	// If any characters were missing, we're screwed
	for _, charSeen := range present {
		if !charSeen {
			return -1
		}
	}

	// Now we are ready to solve the problem
	sols := make([]int, 1<<(len(target)))
	for i := range sols {
		sols[i] = -1
	}
	sols[len(sols)-1] = 0 // Everything covered
	var solve func(coveredCharsBitMask int) int
	solve = func(coveredCharsBitMask int) int {
		if sols[coveredCharsBitMask] == -1 {
			// Need to solve this problem
			record := math.MaxInt32
			for _, sticker := range stickers {
				// Try using this sticker and having it cover all possible target indices it can
				bitMask := coveredCharsBitMask
				for _, bSticker := range []byte(sticker) {
					for i, bTarget := range targetBytes {
						if (bSticker == bTarget) && (((1 << i) & bitMask) == 0) {
							// New coverage
							bitMask = bitMask | (1 << i)
							break
						}
					}
				}
				if bitMask > coveredCharsBitMask {
					// This sticker covered some characters
					record = min(record, 1+solve(bitMask))
				}
			}
			sols[coveredCharsBitMask] = record
		}
		return sols[coveredCharsBitMask]
	}
	return solve(0)
}
