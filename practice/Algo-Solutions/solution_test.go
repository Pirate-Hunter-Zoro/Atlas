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

func testHelperForArrayOutput[I any, A comparable](t *testing.T, f func(i I) []A, inputs []I, expected_outputs [][]A) {
	for idx, input := range inputs {
		output := f(input)
		expected_output := expected_outputs[idx]
		if len(output) != len(expected_output) {
			t.Fatalf("Error - expected array of size %d but got size %d", len(expected_output), len(output))
		}
		for i:=0; i<len(output); i++ {
			if output[i] != expected_output[i] {
				t.Fatalf("Error - expected %v but got %v", expected_output[i], output[i])
			}
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
		{7, 3, [][]int{{2,2},{10,0}}},
		{0, 1, [][]int{{9,6},{8,0},{4,0}}},
	}

	expected_outputs := []int{
		4,
		8,
		3,
		8,
		12,
	}

	f := func(i input) int {
		return maxMoves(i.kx, i.ky, i.positions)
	}

	testHelper(t, f, inputs, expected_outputs)
}

func TestCanFinish(t *testing.T) {
	type input struct {
		numCourses int
		prerequisites [][]int
	}
	inputs := []input{
		{2, [][]int{{1,0}}},
		{2, [][]int{{1,0},{0,1}}},
	}

	expected_outputs := []bool{true, false}

	f := func(i input) bool {
		return canFinish(i.numCourses, i.prerequisites)
	}

	testHelper(t, f, inputs, expected_outputs)
}

func TestIsMatch(t *testing.T) {
	type input struct {
		s string
		p string
	}
	inputs := []input{
		{"aa", "a"},
		{"aa", "*"},
		{"cb", "?a"},
		{"adceb", "*a*b"},
	}

	expected_outputs := []bool{
		false,
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return isMatch(i.s, i.p)
	}

	testHelper(t, f, inputs, expected_outputs)
}

func TestFindSubstring(t *testing.T) {
	type input struct {
		s string
		words []string
	}
	inputs := []input{
		{"barfoothefoobarman", []string{"foo","bar"}},
		{"wordgoodgoodgoodbestword", []string{"word","good","best","word"}},
		{"barfoofoobarthefoobarman", []string{"bar","foo","the"}},
		{"aaaaaaaaaaaaaa", []string{"aa","aa"}},
	}

	expected_outputs := [][]int{
		{0,9},
		{},
		{6,9,12},
		{0,1,2,3,4,5,6,7,8,9,10},
	}

	f := func(i input) []int{
		return findSubstring(i.s, i.words)
	}

	testHelperForArrayOutput(t, f, inputs, expected_outputs)
}

func TestFirstMissingPositive(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1,2,0}},
		{[]int{3,4,-1,1}},
		{[]int{7,8,9,11,12}},
	}

	expected_outputs := []int{
		3,
		2,
		1,
	}

	f := func(i input) int {
		return firstMissingPositive(i.nums)
	}

	testHelper(t, f, inputs, expected_outputs)
}