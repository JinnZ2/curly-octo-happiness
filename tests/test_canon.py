import octahedral_canon as oc


def test_bijection_intact():
    assert oc.is_bijection_intact()


def test_involution():
    for i in range(oc.NUM_VERTICES):
        assert oc.swap_geis_engine(oc.swap_geis_engine(i)) == i


def test_index_range_validation():
    import pytest
    with pytest.raises(ValueError):
        oc.swap_geis_engine(8)
    with pytest.raises(ValueError):
        oc.swap_geis_engine(-1)


def test_position_roundtrip():
    pos = (0.25, -0.25, 0.25)
    eng = oc.geis_position_to_engine_position(pos)
    assert eng == (1.0, -1.0, 1.0)
    back = oc.engine_position_to_geis_position(eng)
    assert back == pos


def test_reconciliation_table_shape():
    table = oc.reconciliation_table()
    assert len(table) == 8
    engine_indices = {e for _, e, _ in table}
    assert engine_indices == set(range(8))
