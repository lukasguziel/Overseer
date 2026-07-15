from overseer.core import model


def test_add_child_sets_parent_and_depth():
    # setup
    root = model.SceneNode("Root", category=model.CAT_NULL)
    child = model.SceneNode("Child")
    grand = model.SceneNode("Grand")

    # do it
    root.add_child(child)
    child.add_child(grand)

    # postcondition
    assert child.parent is root
    assert child.depth == 1
    assert grand.depth == 2


def test_walk_preorder():
    # setup
    root = model.SceneNode("A", category=model.CAT_NULL)
    b = model.SceneNode("B")
    c = model.SceneNode("C")
    root.add_child(b)
    root.add_child(c)

    # postcondition
    assert [n.name for n in root.walk()] == ["A", "B", "C"]


def test_top_group_and_path():
    # setup
    root = model.SceneNode("Group")
    mid = model.SceneNode("Mid")
    leaf = model.SceneNode("Leaf")
    root.add_child(mid)
    mid.add_child(leaf)

    # postcondition
    assert leaf.top_group() is root
    assert leaf.path == "/Group/Mid/Leaf"


def test_tree_helpers(sample_tree):
    # postcondition
    assert sample_tree.by_category(model.CAT_LIGHT).__len__() == 2
    assert len(sample_tree.by_category(model.CAT_CAMERA)) == 1
    guids = [n.guid for n in sample_tree.walk()]
    assert len(guids) == len(set(guids))  # guids are unique
    first = sample_tree.all_nodes()[0]
    assert sample_tree.find(first.guid) is first
