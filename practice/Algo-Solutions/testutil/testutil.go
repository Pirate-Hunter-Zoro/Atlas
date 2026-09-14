package testutil

import (
	"reflect"
	"testing"
)

func RunTestHelper[I, A any](t *testing.T, f func(i I) A, inputs []I, expectedOutputs []A) {
	for idx, input := range inputs {
		output := f(input)
		expectedOutput := expectedOutputs[idx]
		if !reflect.DeepEqual(output, expectedOutput) {
			t.Errorf("Expected output %+v but received %+v", expectedOutput, output)
		}
	}
}
