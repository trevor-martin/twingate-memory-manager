
import pytest
import threading
from memory_manager import (
    MemoryManager,
    DoubleFreeError,
    OutOfMemoryError,
    UseAfterFreeError,
    InvalidBlockError
)


@pytest.fixture
def mm():
    return MemoryManager(1024)

@pytest.fixture
def mm_large():
    return MemoryManager(10000)


class TestBasicInit:
    def test_init(self, mm):
        assert mm.allocated_size == 0
        assert mm.free_size == 1024
        assert mm.total_size == 1024


class TestBasic:
    def test_use_after_free(self, mm):
        b1 = mm.alloc(100)
        mm.free(b1)

        with pytest.raises(UseAfterFreeError):
            b1.write(b"data")

        with pytest.raises(UseAfterFreeError):
            b1.read()

    def test_partial_read(self, mm):
        b1 = mm.alloc(100)
        b1.write(b"This is a test.")

        assert b1.read(2, 5) == b"is"
        assert b1.read(4, 10) == b"test"


class TestAlloc:
    def test_single_alloc(self, mm):
        b1 = mm.alloc(100)

        assert b1.size == 100
        assert mm.allocated_size == 100
        assert mm.free_size == 924

    def test_multiple_allocs(self, mm):
        b1 = mm.alloc(100)
        b2 = mm.alloc(200)
        b3 = mm.alloc(300)

        assert b1.size == 100
        assert b2.size == 200
        assert b3.size == 300
        assert mm.allocated_size == 600
        assert mm.free_size == 424

    def test_alloc_too_much_memory(self, mm):
        with pytest.raises(OutOfMemoryError):
            b1 = mm.alloc(2000)

    def test_invalid_block(self, mm):
        mm2 = MemoryManager(1024)
        b1 = mm.alloc(100)

        with pytest.raises(InvalidBlockError):
            mm2.free(b1)


class TestFree:
    def test_single_free(self, mm):
        b1 = mm.alloc(100)
        mm.free(b1)
        
        assert mm.allocated_size == 0
        assert mm.free_size == 1024

    def test_multiple_frees(self, mm):
        b1 = mm.alloc(100)
        b2 = mm.alloc(100)

        mm.free(b1)
        mm.free(b2)

        assert mm.allocated_size == 0
        assert mm.free_size == 1024

    def test_double_free_error(self, mm):
        b1 = mm.alloc(100)
        mm.free(b1)

        with pytest.raises(DoubleFreeError):
            mm.free(b1)


class TestDefragmentation:
    def test_defragmentation(self):
        mm = MemoryManager(600)
        b1 = mm.alloc(100)
        b2 = mm.alloc(100)
        b3 = mm.alloc(100)
        b4 = mm.alloc(100)
        b5 = mm.alloc(100)

        mm.free(b2)
        mm.free(b4)

        b6 = mm.alloc(300)

        assert b6 is not None
        assert b6.size == 300

    def test_out_of_memory(self):
        mm = MemoryManager(600)
        b1 = mm.alloc(100)
        b2 = mm.alloc(100)
        b3 = mm.alloc(100)
        b4 = mm.alloc(100)
        b5 = mm.alloc(100)

        mm.free(b2)
        mm.free(b4)

        with pytest.raises(OutOfMemoryError) as exc_info:
            b6 = mm.alloc(400)

        assert exc_info.value.requested_size == 400
        assert exc_info.value.available_size == 300

    def test_coalesce_after_free(self, mm):
        b1 = mm.alloc(100)
        b2 = mm.alloc(100)
        b3 = mm.alloc(100)
        b4 = mm.alloc(100)

        mm.free(b2)
        mm.free(b4)

        assert len(mm._free_blocks) == 2

    def test_clean_memory_after_free(self, mm):
        b1 = mm.alloc(4)
        b1.write(b"data")
        
        mm.free(b1)

        b2 = mm.alloc(4)

        assert b2.read() == b'\x00\x00\x00\x00'

    def test_moved_data(self, mm):
        b1 = mm.alloc(4)
        b2 = mm.alloc(4)
        b3 = mm.alloc(4)

        b1.write(b"here")
        b2.write(b"gone")
        b3.write(b"data")

        mm.free(b2)

        assert b3.read() == b"data"


class TestThreading:
    def test_threading(self, mm_large):
        errors = []
        def worker():

            for _ in range(50):
                try:
                    block = mm_large.alloc(50)
                    block.write(b"data")
                    mm_large.free(block)
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
