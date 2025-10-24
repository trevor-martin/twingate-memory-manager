
from typing import List, Optional
from threading import RLock


class MemoryManagerError(Exception):
    pass


class InvalidSizeError(MemoryManagerError):
    def __init__(self, size: int):
        self.size = size
        super().__init__(
            f"Invalid size. size: {size}"
        )


class InvalidBlockError(MemoryManagerError):
    pass


class UseAfterFreeError(InvalidBlockError):
    def __init__(self, block_id: int):
        self.block_id = block_id
        super().__init__(f"Block cannot be accessed after being freed. block_id: {block_id}")


class OutOfMemoryError(MemoryManagerError):
    def __init__(self, requested_size: int, available_size: int):
        self.requested_size = requested_size
        self.available_size = available_size
        super().__init__(
            f"Out of memory. "
            f"Requested size: {requested_size}, Available size: {available_size}"
        )


class DoubleFreeError(InvalidBlockError):
    def __init__(self, block_id: int):
        self.block_id = block_id
        super().__init__(
            f"This block has already been freed. block_id: {block_id}"
        )


class OutOfBoundsError(InvalidBlockError):
    def __init__(self, operation: str, size: int):
        self.operation = operation
        self.size = size
        super().__init__(
            f"{operation} is out of bounds. size: {size}"
        )


class MemoryBlock:

    _next_id = 0

    def __init__(self, start, size, buffer):
        self.block_id = MemoryBlock._next_id
        MemoryBlock._next_id += 1

        self.start = start
        self.size = size
        self._buffer = buffer
        self._freed = False

    @property
    def end(self) -> int:
        return self.start + self.size
    
    @property
    def is_freed(self):
        return self._freed
    
    def mark_freed(self):
        self._freed = True

    def write(self, data: bytes, offset: int = 0) -> None:
        if self._freed:
            raise UseAfterFreeError(self.block_id)
        
        if offset + len(data) > self.size:
            raise OutOfBoundsError("Write", offset + len(data))
        
        write_start = self.start + offset
        write_end = write_start + len(data)

        self._buffer[write_start:write_end] = data

    def read(self, size: Optional[int] = None, offset: int = 0) -> bytes:
        if self._freed:
            raise UseAfterFreeError(self.block_id)

        if size is None:
            size = self.size - offset

        if offset + size > self.size:
            raise OutOfBoundsError("Read", offset + size)
        
        read_start = self.start + offset
        read_end = read_start + size

        return bytes(self._buffer[read_start:read_end])


class FreeBlock:
    def __init__(self, start: int, size: int):
        self.start = start
        self.size = size

    @property
    def end(self) -> int:
        return self.start + self.size


class MemoryManager:
    def __init__(self, size: int):
        self._buffer = bytearray(size)
        self._lock = RLock()
        self._total_size = size
        self._allocated_blocks: List[MemoryBlock] = []
        self._free_blocks: List[FreeBlock] = [FreeBlock(0, size)]

    @property
    def total_size(self) -> int:
        return self._total_size
    
    @property
    def allocated_size(self) -> int:
        with self._lock:
            return sum(block.size for block in self._allocated_blocks)
        
    @property
    def free_size(self) -> int:
        with self._lock:
            return sum(block.size for block in self._free_blocks)
        
    def alloc(self, size: int) -> MemoryBlock:
        if size <= 0:
            raise InvalidSizeError(size)
        
        with self._lock:
            free_block = self._find_free_block(size)

            if free_block is None:
                self._defragmentation()

                free_block = self._find_free_block(size)

                if free_block is None:
                    raise OutOfMemoryError(size, self.free_size)
                
            block = MemoryBlock(free_block.start, size, self._buffer)
            self._allocated_blocks.append(block)

            remaining_size = free_block.size - size
            self._free_blocks.remove(free_block)

            if remaining_size > 0:
                self._free_blocks.append(
                    FreeBlock(block.start + size, remaining_size)
                )

            return block

    def free(self, block: MemoryBlock):
        with self._lock:
            if block not in self._allocated_blocks:
                if block.is_freed:
                    raise DoubleFreeError(block.block_id)
                raise InvalidBlockError(
                    f"This block is not manager by this memory manager. block_id: {block.block_id}"
                )

            self._buffer[block.start:block.end] = b'\x00' * block.size

            block.mark_freed()

            self._allocated_blocks.remove(block)
            
            free_block = FreeBlock(block.start, block.size)
            self._free_blocks.append(free_block)

            self._free_blocks.sort(key=lambda b: b.start)
            self._coalesce_free_blocks()

    def defragmentation(self):
        with self._lock:
            return self._defragmentation()

    def _defragmentation(self):
        self._allocated_blocks.sort(key=lambda b: b.start)

        moved_blocks = 0
        current_position = 0

        for block in self._allocated_blocks:
            if block.start != current_position:

                self._move_block(block, current_position)
                moved_blocks +=1
            
            current_position += block.size

        total_allocated = sum(b.size for b in self._allocated_blocks)
        if total_allocated < self.total_size:
            self._free_blocks = [
                FreeBlock(total_allocated, self.total_size - total_allocated)
            ]
        else:
            self._free_blocks = []


        return moved_blocks

    def _move_block(self, block: MemoryBlock, new_start: int):
        if block.start == new_start:
            return
        
        old_start = block.start
        old_end = block.end
        new_end = new_start + block.size

        self._buffer[new_start:new_end] = self._buffer[old_start:old_end]

        block.start = new_start

    def _find_free_block(self, size: int) -> Optional[FreeBlock]:
        for free_block in self._free_blocks:
            if free_block.size >= size:
                return free_block
        
        return None

    def _coalesce_free_blocks(self):

        coalesced = []
        current = self._free_blocks[0]

        for next_block in self._free_blocks[1:]:
            if current.end == next_block.start:
                current = FreeBlock(current.start, current.size + next_block.size)
            else:
                coalesced.append(current)
                current = next_block

        coalesced.append(current)
        self._free_blocks = coalesced
