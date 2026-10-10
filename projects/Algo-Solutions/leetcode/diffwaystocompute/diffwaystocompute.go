package diffwaystocompute

import (
	"regexp"
	"strconv"
)

func diffWaysToCompute(expression string) []int {
	// Create list of numbers
	re := regexp.MustCompile(`[\+\*\-]`)
	numbersStrs := re.Split(expression, -1)
	nums := make([]int, len(numbersStrs))
	for i:=range nums {
		num, _ := strconv.Atoi(numbersStrs[i])
		nums[i] = num
	}

	// Create list of operators
	op_map := make(map[rune]rune)
	op_map['+'] = '+'
	op_map['-'] = '-'
	op_map['*'] = '*'
	operators := []rune{}
	for i:=range expression {
		if op, ok := op_map[rune(expression[i])]; ok {
			operators = append(operators, op)
		}
	}

	// Store results
	results := make([][][]int, len(nums))
	for i:=range results {
		results[i] = make([][]int, len(nums))
		for j:=range results[i] {
			results[i][j] = []int{}
		}
	}

	// Recursive solver
	var solve func(start int, end int) []int;
	solve = func(start int, end int) []int {
		if len(results[start][end]) == 0 {
			// Need to solve this problem
			switch start {
				case end:
					// Base case
					results[start][end] = append(results[start][end], nums[start])
				case end - 1:
					// Also base case
					operator := operators[start]
					switch operator {
						case '-':
							results[start][end] = append(results[start][end], nums[start] - nums[end])
						case '*':
							results[start][end] = append(results[start][end], nums[start] * nums[end])
						default:
							results[start][end] = append(results[start][end], nums[start] + nums[end])
					}
				default:
					// Non base case - try each sign being last
					for op_idx := start; op_idx < end; op_idx++ {
						operator := operators[op_idx]
						left_sols := solve(start, op_idx)
						right_sols := solve(op_idx+1, end)
						for _, ls := range left_sols {
							for _, rs := range right_sols {
								switch operator {
									case '-':
										results[start][end] = append(results[start][end], ls - rs)
									case '*':
										results[start][end] = append(results[start][end], ls * rs)
									default:
										results[start][end] = append(results[start][end], ls + rs)
								}
							}
						}
					}
			}
		}
		return results[start][end]
	}

    return solve(0, len(nums)-1)
}