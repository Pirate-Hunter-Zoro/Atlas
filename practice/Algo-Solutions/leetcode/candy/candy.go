package candy

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

	candiesNeeded := make(map[int]int)
	total := 0
	for i := range ratings {
		total += computeNeededCandies(i, candiesNeeded, graph)
	}
	return total
}

func computeNeededCandies(i int, candiesNeeded map[int]int, graph [][]int) int {
	_, ok := candiesNeeded[i]
	if !ok {
		// Need to solve this problem
		maxChild := 0
		for _, child := range graph[i] {
			maxChild = max(maxChild, computeNeededCandies(child, candiesNeeded, graph))
		}
		candiesNeeded[i] = maxChild + 1
	}

	return candiesNeeded[i]
}
