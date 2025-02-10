package leetcode

import "testing"

func testHelper[I any, A comparable](t *testing.T, f func(i I) A, inputs []I, expected_outputs []A) {
	for idx, input := range inputs {
		output := f(input)
		expected_output := expected_outputs[idx]
		if output != expected_output {
			t.Fatalf("Error - expected %v but got %v", expected_output, output)
		}
	}
}

func TestSuperEggDrop(t *testing.T) {
	type input struct {
		n int
		k int
	}

	inputs := []input{
		{n:1, k:2},
		{n:2, k:6},
		{n:3, k:14},
		{n:1, k:1},
		{n:7, k:5000},
	}

	expected_outputs := []int{
		2,3,4,1,13,
	}

	f := func(i input) int {
		return superEggDrop(i.n, i.k)
	}

	testHelper(t, f, inputs, expected_outputs)
}

func TestLargestRectangleArea(t *testing.T) {
	type input struct {
		heights []int
	}
	inputs := []input{
		{heights : []int{2,1,5,6,2,3}},
		{heights : []int{2,4}},
	}
	
	expected_outputs := []int{
		10,
		4,
	}

	f := func(i input) int {
		return largestRectangleArea(i.heights)
	}

	testHelper(t, f, inputs, expected_outputs)
}

func TestMaximalRectangle(t *testing.T) {
	type input struct {
		matrix [][]byte
	}
	inputs := []input{
		{matrix: [][]byte{{'1','0','1','0','0'},{'1','0','1','1','1'},{'1','1','1','1','1'},{'1','0','0','1','0'}}},
		{matrix: [][]byte{{'0'}}},
		{matrix: [][]byte{{'1'}}},
	}

	expected_outputs := []int{
		6,0,1,
	}

	f := func(i input) int {
		return maximalRectangle(i.matrix)
	}

	testHelper(t, f, inputs, expected_outputs)
}

func TestMaxMove(t *testing.T) {
	type input struct {
		kx int
		ky int
		positions [][]int
	}

	inputs := []input{
		{1, 1, [][]int{{0,0}}},
		{0, 2, [][]int{{1,1},{2,2},{3,3}}},
		{0, 0, [][]int{{1,2},{2,4}}},
	}

	expected_outputs := []int{
		4,
		8,
		3,
	}

	f := func(i input) int {
		return maxMoves(i.kx, i.ky, i.positions)
	}

	testHelper(t, f, inputs, expected_outputs)
}