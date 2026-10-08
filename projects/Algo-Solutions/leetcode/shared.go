package leetcode

import (
	"algo-solutions/helpermath"
)

// GlobalCalculator is the shared combinatorics helper, initialized once.
var GlobalCalculator *helpermath.ChooseCalculator

func init() {
	GlobalCalculator = helpermath.NewChooseCalculator()
}

// MOD value for when modular arithmetic must be performed
var MOD int = 1000000007
