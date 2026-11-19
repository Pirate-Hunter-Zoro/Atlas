package dynamicarray

type dynamicarray[T any] struct {
	data []T
	n    int
}

func New[T any]() *dynamicarray[T] {
	return &dynamicarray[T]{
		[]T{},
		0,
	}
}
func (d *dynamicarray[T]) Len() int {
	return d.n
}
func (d *dynamicarray[T]) Set(i int, v T) {
	d.data[i] = v
}
func (d *dynamicarray[T]) Cap() int {
	return cap(d.data)
}
func (d *dynamicarray[T]) At(i int) T {
	return d.data[i]
}
func (d *dynamicarray[T]) Append(v T) {
	d.n++
	if d.Cap() < d.Len() {
		// Double if at full capacity - amortizes to constant append
		data_copy := make([]T, 2*d.n)
		copy(data_copy, d.data)
		d.data = data_copy
	}
	d.data[d.n-1] = v
}
