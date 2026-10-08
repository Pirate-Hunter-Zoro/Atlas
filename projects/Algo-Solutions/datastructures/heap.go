package datastructures

type Heap[T any] struct {
	array            []T
	goesHigherOnHeap func(first T, second T) bool
	size             int
}

func NewHeap[T any](goesHigherOnHeap func(first T, second T) bool) *Heap[T] {
	return &Heap[T]{
		[]T{},
		goesHigherOnHeap,
		0,
	}
}
func (h *Heap[T]) Push(t T) {
	h.array = append(h.array, t)
	h.size++
	h.fixHeapUp()
}
func (h *Heap[T]) fixHeapUp() {
	current := len(h.array) - 1
	parent := (current - 1) / 2
	for parent >= 0 && parent < current && h.goesHigherOnHeap(h.array[current], h.array[parent]) {
		temp := h.array[current]
		h.array[current] = h.array[parent]
		h.array[parent] = temp
		current = parent
		parent = (current - 1) / 2
	}
}
func (h *Heap[T]) Peek() T {
	return h.array[0]
}
func (h *Heap[T]) Pop() T {
	v := h.array[0]
	if len(h.array) == 1 {
		h.array = []T{}
	} else {
		h.array[0] = h.array[len(h.array)-1]
		h.array = h.array[:len(h.array)-1]
		h.fixHeapDown()
	}
	h.size--
	return v
}
func (h *Heap[T]) fixHeapDown() {
	current := 0
	leftChild := 2*(current) + 1
	rightChild := 2 * (current + 1)
	for leftChild < len(h.array) {
		upperChild := leftChild
		if rightChild < len(h.array) && h.goesHigherOnHeap(h.array[rightChild], h.array[leftChild]) {
			upperChild = rightChild
		}
		if h.goesHigherOnHeap(h.array[upperChild], h.array[current]) {
			temp := h.array[current]
			h.array[current] = h.array[upperChild]
			h.array[upperChild] = temp
			current = upperChild
		} else {
			break
		}
		leftChild = 2*(current) + 1
		rightChild = 2 * (current + 1)
	}
}
func (h *Heap[T]) Empty() bool {
	return len(h.array) == 0
}
func (h *Heap[T]) Size() int {
	return h.size
}
