from sceneorg.core import model


def test_add_child_sets_parent_and_depth():
    root = model.SceneNode("Root", category=model.CAT_NULL)
    child = model.SceneNode("Child")
    root.add_child(child)
    assert child.parent is root
    assert child.depth == 1
    grand = model.SceneNode("Grand")
    child.add_child(grand)
    assert grand.depth == 2


def test_walk_preorder():
    root = model.SceneNode("A", category=model.CAT_NULL)
    b = model.SceneNode("B")
    c = model.SceneNode("C")
    root.add_child(b)
    root.add_child(c)
    assert [n.name for n in root.walk()] == ["A", "B", "C"]


def test_top_group_and_path():
    root = model.SceneNode("Group")
    mid = model.SceneNode("Mid")
    leaf = model.SceneNode("Leaf")
    root.add_child(mid)
    mid.add_child(leaf)
    assert leaf.top_group() is root
    assert leaf.path == "/Group/Mid/Leaf"


def test_tree_helpers(sample_tree):
    assert sample_tree.by_category(model.CAT_LIGHT).__len__() == 2
    assert len(sample_tree.by_category(model.CAT_CAMERA)) == 1
    # guids are unique
    guids = [n.guid for n in sample_tree.walk()]
    assert len(guids) == len(set(guids))
    first = sample_tree.all_nodes()[0]
    assert sample_tree.find(first.guid) is first
