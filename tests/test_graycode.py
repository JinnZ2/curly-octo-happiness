from grounding.core.graycode import gray_bits, gray_to_index

BANDS = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]


def test_band_edges():
    assert gray_to_index(gray_bits(0.0, BANDS)) == 0
    assert gray_to_index(gray_bits(0.99, BANDS)) == 0
    assert gray_to_index(gray_bits(1.0, BANDS)) == 1     # threshold is inclusive
    assert gray_to_index(gray_bits(7.0, BANDS)) == 7
    assert gray_to_index(gray_bits(1e9, BANDS)) == 7     # clamps to top band


def test_below_first_band():
    assert gray_to_index(gray_bits(-5.0, BANDS)) == 0


def test_roundtrip_all_bands():
    for i in range(8):
        assert gray_to_index(gray_bits(float(i), BANDS)) == i


def test_adjacent_bands_differ_by_one_bit():
    codes = [gray_bits(float(i), BANDS) for i in range(8)]
    for a, b in zip(codes, codes[1:]):
        assert sum(x != y for x, y in zip(a, b)) == 1


def test_n_bits():
    assert len(gray_bits(3.0, BANDS, n_bits=5)) == 5
