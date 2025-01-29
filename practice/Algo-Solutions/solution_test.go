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
		return SuperEggDrop(i.n, i.k)
	}

	testHelper(t, f, inputs, expected_outputs)
}