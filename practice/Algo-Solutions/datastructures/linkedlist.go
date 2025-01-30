package datastructures

type node[T any] struct {
	value T
	next *node[T]
}

type Queue[T any] struct {
	head *node[T]
	tail *node[T]
}
func NewQueue[T any]() *Queue[T] {
	return &Queue[T]{
		head : nil,
	}
}
func (q *Queue[T]) Dequeue() T {
	v := q.head.value
	q.head = q.head.next
	return v
}
func (q *Queue[T]) Peek() T {
	return q.head.value
}
func (q *Queue[T]) Enqueue(v T){
	if q.head == nil {
		q.head = &node[T]{value: v}
		q.tail = q.head
	} else {
		q.tail.next = &node[T]{value: v}
		q.tail = q.tail.next
	}
}
func (q *Queue[T]) Empty() bool {
	return q.head == nil
}

type Stack[T any] struct {
	head *node[T]
}
func NewStack[T any]() *Stack[T] {
	return &Stack[T]{
		head : nil,
	}
}
func (s *Stack[T]) Pop() T {
	v := s.head.value
	s.head = s.head.next
	return v
}
func (s *Stack[T]) Peek() T {
	return s.head.value
}
func (s *Stack[T]) Push(v T){
	if s.head == nil {
		s.head = &node[T]{value: v}
	} else {
		new_head := &node[T]{value: v}
		new_head.next = s.head
		s.head = new_head
	}
}
func (s *Stack[T]) Empty() bool {
	return s.head == nil
}