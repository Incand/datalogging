import pytest

from datalogging.logger import LogNode, Logger, _split_vpath, _rsplit_vpath


def test_split_vpath():
    assert _split_vpath('') == ('', '')
    assert _split_vpath('asdf') == ('asdf', '')
    assert _split_vpath('asdf/qwer') == ('asdf', 'qwer')
    assert _split_vpath('asdf/qwer/yxcv') == ('asdf', 'qwer/yxcv')


def test_rsplit_vpath():
    assert _rsplit_vpath('') == ('', '')
    assert _rsplit_vpath('asdf') == ('', 'asdf')
    assert _rsplit_vpath('asdf/qwer') == ('asdf', 'qwer')
    assert _rsplit_vpath('asdf/qwer/yxcv') == ('asdf/qwer', 'yxcv')


class TestLogNode:
    @pytest.fixture()
    def node(self):
        return LogNode()

    @pytest.fixture()
    def child_node(self, node):
        return node.children.setdefault('child', LogNode())

    def test_clearing_empties_data_dict(self, node):
        node.data['vals'] = [1]
        node.clear()
        assert node.data == {}

    def test_clearing_clears_children(self, node, child_node):
        child_node.data['vals'] = [1, 2, 3]
        node.clear()
        assert child_node.data == {}

    def test_parsing_parses_child(self, node, child_node):
        child_node.data['vals'] = [1, 2, 3]
        assert node.parse() == {'child': {'vals': [1, 2, 3]}}

    def test_parsing_does_not_parse_empty_child(self, node, child_node):
        assert 'child' in node.children
        assert node.parse() == {}


class TestLogger:
    @pytest.fixture()
    def logger(self):
        return Logger()

    @pytest.fixture()
    def child_logger(self, logger):
        return logger.make_child('child')

    def test_making_child_creates_one_at_correct_location(self, logger):
        vpath = '1/2/3'
        child_logger = logger.make_child(vpath)
        assert child_logger._root == logger._traverse(vpath)

    def test_getitem_returns_correct_data(self, logger, child_logger):
        child_logger._root.data['vals'] = [1]
        assert logger['child/vals'] == [1]
        assert child_logger['vals'] == [1]

    def test_getitem_returns_reference_to_data(self, logger, child_logger):
        child_logger._root.data['vals'] = ref = [1]
        assert id(logger['child/vals']) == id(ref)
        assert id(child_logger['vals']) == id(ref)

    def test_getitem_raises_keyerror_for_invalid_datakey(self, logger, child_logger):
        # root node should not have data entry with empty key
        with pytest.raises(KeyError):
            _ = logger['']
        # 'child' is a key in node children, not in node data
        with pytest.raises(KeyError):
            _ = logger['child']
        # child node should not have data entry with empty key
        with pytest.raises(KeyError):
            _ = logger['child/']
        # child node should not have data entry with key 'nonexistent'
        with pytest.raises(KeyError):
            _ = logger['child/nonexistent']

    def test_get_returns_correct_existing_item(self, logger, child_logger):
        child_logger._root.data['vals'] = [1]
        assert logger.get('child/vals') == logger['child/vals']
        assert child_logger.get('vals') == child_logger['vals']

    def test_get_returns_default_on_nonexisting_item(self, logger, child_logger):
        assert logger.get('child/vals') is None
        assert child_logger.get('vals') is None
        assert logger.get('child/vals', [2]) == [2]
        assert child_logger.get('vals', [3]) == [3]

    def test_logging_single_value_appends_it_to_data(self, logger):
        logger.log('vals', 1)
        assert logger.get('vals') == [1]
        logger.log('vals', 2)
        assert logger.get('vals') == [1, 2]

    def test_logging_in_child_is_visible_in_parent(self, logger, child_logger):
        child_logger.log('vals', 1)
        assert logger.get('child/vals') == [1]

    def test_logging_in_parent_at_correct_location_is_visible_in_child(self, logger, child_logger):
        logger.log('child/vals', 1)
        assert child_logger.get('vals') == [1]

    def test_logging_multiple_values_extends_data(self, logger):
        logger.log('vals', [1, 2, 3])
        assert logger.get('vals') == [1, 2, 3]
        logger.log('vals', [4, 5, 6])
        assert logger.get('vals') == [1, 2, 3, 4, 5, 6]

    def test_as_dict(self, logger, child_logger):
        assert logger.as_dict() == {}
        assert child_logger.as_dict() == {}

        logger.log('vals', 1)
        assert logger.as_dict() == {'vals': [1]}
        assert child_logger.as_dict() == {}

        logger.log('child/vals', 2)
        assert logger.as_dict() == {'vals': [1], 'child': {'vals': [2]}}
        assert child_logger.as_dict() == {'vals': [2]}

    def test_clear_parent_removes_data_from_child(self, logger, child_logger):
        child_logger.log('vals', 1)
        logger.clear()
        assert child_logger.as_dict() == {}

    def test_clear_child_does_not_remove_data_from_parent(self, logger, child_logger):
        logger.log('vals', 1)
        child_logger.clear()
        assert logger.as_dict() == {'vals': [1]}
