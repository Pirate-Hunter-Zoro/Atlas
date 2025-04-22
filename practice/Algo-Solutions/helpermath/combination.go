package helpermath

type ChooseCalculator struct {
	sols map[int]map[int]int
	solsMod map[int]map[int]int
}

func NewChooseCalculator() *ChooseCalculator {
	calculator := &ChooseCalculator{
		sols : make(map[int]map[int]int),
		solsMod: make(map[int]map[int]int),
	}
	return calculator
}

func (calculator *ChooseCalculator) Choose(n int, k int) int {
	if k > n {
		return 0
	} else if k == n {
		return 1
	} else if k == 0 {
		return 1
	} else {
		_, ok := calculator.sols[n]
		if !ok {
			calculator.sols[n] = make(map[int]int)
		}
		_, ok = calculator.sols[n][k]
		if !ok {
			calculator.sols[n][k] = calculator.Choose(n-1, k) + calculator.Choose(n-1,k-1)
		}
		return calculator.sols[n][k]
	}
}

func (calculator *ChooseCalculator) ChooseMod(n int, k int) int {
	if k > n {
		return 0
	} else if k == n {
		return 1
	} else if k == 0 {
		return 1
	} else {
		_, ok := calculator.solsMod[n]
		if !ok {
			calculator.solsMod[n] = make(map[int]int)
		}
		_, ok = calculator.solsMod[n][k]
		if !ok {
			calculator.solsMod[n][k] = ModAdd(calculator.ChooseMod(n-1, k), calculator.ChooseMod(n-1,k-1))
		}
		return calculator.solsMod[n][k]
	}
}