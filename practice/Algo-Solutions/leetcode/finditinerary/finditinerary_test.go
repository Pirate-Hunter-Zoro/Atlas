package finditinerary

import (
	"algo-solutions/testutil"
	"testing"
)

func TestFindItinerary(t *testing.T) {
	type input struct {
		tickets [][]string
	}
	inputs := []input{
		{[][]string{{"MUC", "LHR"}, {"JFK", "MUC"}, {"SFO", "SJC"}, {"LHR", "SFO"}}},
		{[][]string{{"JFK", "SFO"}, {"JFK", "ATL"}, {"SFO", "ATL"}, {"ATL", "JFK"}, {"ATL", "SFO"}}},
	}
	expectedOutputs := [][]string{
		{"JFK", "MUC", "LHR", "SFO", "SJC"},
		{"JFK", "ATL", "JFK", "SFO", "ATL", "SFO"},
	}

	f := func(i input) []string {
		return findItinerary(i.tickets)
	}
	testutil.RunTestHelper(t, f, inputs, expectedOutputs)
}
