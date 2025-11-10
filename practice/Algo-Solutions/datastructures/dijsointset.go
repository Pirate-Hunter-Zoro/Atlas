package datastructures

type setnode[T any] struct {
	val T
	parent *setnode[T]
}
func (n *setnode[T]) collapse() {
	// Compress the ancestor hiearchy
	if n.parent != nil {
		n.parent.collapse()
		if n.parent.parent != nil {
			n.parent = n.parent.parent
		}
	}
}
func (n *setnode[T]) merge(other *setnode[T]) {
	if n != other {
		if n.parent == nil && other.parent == nil {
			// WLOG, make the first one the parent
			other.parent = n
		} else if n.parent == nil {
			// The other node has a parent - collapse its hierarchy and make 'n' have the same parent
			other.collapse()
			n.parent = other.parent
		} else if other.parent == nil {
			// Vice versa
			n.collapse()
			other.parent = n.parent
		} else {
			// Both have non nil parents
			n.collapse()
			other.collapse()
			n.parent.parent = other.parent
			n.collapse()
		}
	}
}

type DisjointSet[T comparable] struct {
	nodes map[T]*setnode[T]
}
func NewDisjointSet[T comparable]() *DisjointSet[T] {
	return &DisjointSet[T]{
		make(map[T]*setnode[T]),
	}
}
func (set *DisjointSet[T]) Add(v T) {
	_, ok := set.nodes[v]
	if !ok {
		// Add in this new value
		set.nodes[v] = &setnode[T]{
			v,
			nil,
		}
	}
}
func (set *DisjointSet[T]) Join(v1 T, v2 T) {
	node1, ok := set.nodes[v1]
	if ok {
		node2, ok := set.nodes[v2]
		if ok {
			// Both nodes do exist
			node1.merge(node2)
		}
	}
}
func (set *DisjointSet[T]) Same(v1 T, v2 T) bool {
	node1, ok := set.nodes[v1]
	if ok {
		node2, ok := set.nodes[v2]
		if ok {
			// Both nodes do exist
			node1.collapse()
			node2.collapse()
			return (node1 == node2) || (node1.parent == node2) || (node2.parent == node1) || (node1.parent == node2.parent && (node1.parent != nil))
		} else {
			return false
		}
	} else {
		return false
	}
}