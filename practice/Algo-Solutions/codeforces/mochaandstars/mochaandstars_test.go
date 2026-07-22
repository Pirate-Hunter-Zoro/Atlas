package main

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMochaAndStars(t *testing.T) {
	type input struct {
		n int
		m int
		l []int
		r []int
	}
	inputs := []input{
		{2, 4, []int{1,1}, []int{3,2}},
		{5, 10, []int{1,1,1,1,1}, []int{10,10,10,10,10}},
		{5, 100, []int{1,1,1,4,6}, []int{94,96,91,96,97}},
	}

	expectedOutputs := []int{
		4,
		251,
		47464146,
	}

	f := func(i input) int {
		return solve(i.n, i.m, i.l, i.r)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
