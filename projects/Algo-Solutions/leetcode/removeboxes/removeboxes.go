package removeboxes

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

func recRemoveBoxes(boxes []int, left int, right int, numSame int, sols [][][]int) int {
	// What is our start index, what is our end index, and how many boxes immediately to the left are the same as boxes[left]?
	if sols[left][right][numSame] == -1 {
		if left == right {
			// Base case - only one box left
			sols[left][right][numSame] = (numSame + 1) * (numSame + 1)
		} else {
			// While boxes[left] == boxes[left+1], increment numSame and move the left pointer
			oldLeft := left
			oldNumSame := numSame
			for left < right && boxes[left] == boxes[left+1] {
				numSame++
				left++
			}
			// Note that we can be greedy like this because (a+b)^2 > a^2 + b^2
			// Two options
			// 1. Remove all boxes from left+1 to right first, and then remove the (k+1) boxes of value boxes[left]
			option1 := (numSame + 1) * (numSame + 1)
			if left < right {
				option1 += recRemoveBoxes(boxes, left+1, right, 0, sols)
			}
			// 2. Find all next boxes with the same value as boxes[left] and remove all boxes in between
			option2 := 0
			for j := left + 2; j <= right; j++ {
				if boxes[j] == boxes[left] {
					// We can remove all boxes from left+1 to j-1, and then start at index j+1 with (k+1) boxes to equal to boxes[newLeft=j]
					option2 = max(option2, recRemoveBoxes(boxes, left+1, j-1, 0, sols)+recRemoveBoxes(boxes, j, right, numSame+1, sols))
				}
			}
			bestOption := max(option1, option2)
			sols[left][right][numSame] = bestOption
			// If we moved up our initial left pointer, store all those solutions too
			for i := oldLeft; i < left; i++ {
				prevNumSame := numSame - (left - i)
				sols[i][right][prevNumSame] = bestOption
			}
			left = oldLeft
			numSame = oldNumSame
		}
	}
	return sols[left][right][numSame]
}
