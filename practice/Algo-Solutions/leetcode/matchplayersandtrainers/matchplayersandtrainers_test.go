package matchplayersandtrainers

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMatchPlayersAndTrainers(t *testing.T) {
	type input struct {
		players  []int
		trainers []int
	}
	inputs := []input{
		{[]int{4, 7, 9}, []int{8, 2, 5, 8}},
		{[]int{1, 1, 1}, []int{10}},
	}

	expectedOutputs := []int{
		2,
		1,
	}

	f := func(i input) int {
		return matchPlayersAndTrainers(i.players, i.trainers)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
