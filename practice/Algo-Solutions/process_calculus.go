package leetcode

type NodeType int;

const (
	Name NodeType = iota
	Agent
	Nil
	Wildcard
	Tuple
)

type Node struct {
	Type NodeType
	IsValue bool
	IsBindable bool
	Text string
	Children []*Node
}

func evaluateMatch(v *Node, x *Node, bindings_map map[string]*Node) bool {
	// Both tuples
	if v.Type == NodeType(Tuple) && x.Type == NodeType(Tuple) {
		if len(v.Children) != len(x.Children) {
			return false
		}
		for idx := range v.Children {
			v_child := v.Children[idx]
			x_child := x.Children[idx]
			if !evaluateMatch(v_child, x_child, bindings_map) {
				return false
			}
		}
		// All children passed
		return true
	} else if v.IsBindable && x.Type == NodeType(Wildcard) {
		// X is bound to whatever value V is, and that's perfectly fine
		bindings_map[x.Text] = v
		return true
	} else {
		// Because we do not check for 'IsBindable' flag, this covers V#~V, V~V#, V#~V#, and V~V
		return v.Text == x.Text && v.Type == x.Type
	}
}