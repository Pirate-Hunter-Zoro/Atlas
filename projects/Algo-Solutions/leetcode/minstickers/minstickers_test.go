package minstickers

import (
	"algo-solutions/testutil"
	"testing"
)

func TestMinStickers(t *testing.T) {
	type input struct {
		stickers []string
		target   string
	}
	inputs := []input{
		{[]string{"with", "example", "science"}, "thehat"},
		{[]string{"notice", "possible"}, "basicbasic"},
		{[]string{"these", "guess", "about", "garden", "him"}, "atomher"},
	}

	expectedOutputs := []int{
		3,
		-1,
		3,
	}

	f := func(i input) int {
		return minStickers(i.stickers, i.target)
	}

	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
