package datastructures

type Heap[T any] struct {
	array []T
	goes_higher_on_heap func(first T, second T) bool
	size int
}
func NewHeap[T any](goes_higher_on_heap func(first T, second T) bool) *Heap[T] {
	return &Heap[T]{
		[]T{},
		goes_higher_on_heap,
		0,
	}
} 
func (h *Heap[T]) Push(t T) {
	h.array = append(h.array, t)
	h.size++
	h.fixHeapUp()
}
func (h *Heap[T]) fixHeapUp() {
	current := len(h.array)-1
	parent := (current-1)/2
	for parent >= 0 && parent < current &&  h.goes_higher_on_heap(h.array[current],h.array[parent]){
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
	return v
}
func (h *Heap[T]) fixHeapDown() {
	current := 0
	left_child := 2*(current) + 1
	right_child := 2*(current + 1)
	for left_child < len(h.array) {
		upper_child := left_child
		if right_child < len(h.array) && h.goes_higher_on_heap(h.array[right_child],h.array[left_child]) {
			upper_child = right_child
		}
		if h.goes_higher_on_heap(h.array[upper_child],h.array[current]) {
			temp := h.array[current]
			h.array[current] = h.array[upper_child]
			h.array[upper_child] = temp
			current = upper_child
		} else {
			break
		}
		left_child = 2*(current) + 1
		right_child = 2*(current + 1)
	}
}
func (h *Heap[T]) Empty() bool {
	return len(h.array) == 0
}