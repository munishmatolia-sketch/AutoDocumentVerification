"""Progress tracking for upload operations."""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class ProgressStatus(str, Enum):
    """Progress status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressInfo:
    """Progress information for an upload operation."""
    id: str = field(default_factory=lambda: str(int(time.time() * 1000000)))
    filename: str = ""
    total_size: int = 0
    processed_size: int = 0
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_size == 0:
            return 0.0
        return min(100.0, (self.processed_size / self.total_size) * 100.0)
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Calculate elapsed time in seconds."""
        if self.start_time is None:
            return None
        end_time = self.end_time or time.time()
        return end_time - self.start_time
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if (self.start_time is None or 
            self.processed_size == 0 or 
            self.status != ProgressStatus.IN_PROGRESS):
            return None
        
        elapsed = self.elapsed_time
        if elapsed is None or elapsed == 0:
            return None
        
        remaining_size = self.total_size - self.processed_size
        if remaining_size <= 0:
            return 0.0
        
        rate = self.processed_size / elapsed
        return remaining_size / rate if rate > 0 else None


class ProgressTracker:
    """Tracks progress for upload operations."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self._progress_info: Dict[str, ProgressInfo] = {}
        self._callbacks: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    async def create_progress(self, filename: str, total_size: int, 
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new progress tracker for an upload.
        
        Args:
            filename: Name of the file being uploaded
            total_size: Total size of the file in bytes
            metadata: Optional metadata for the upload
            
        Returns:
            ID of the created progress tracker
        """
        async with self._lock:
            progress_id = str(int(time.time() * 1000000))
            self._progress_info[progress_id] = ProgressInfo(
                id=progress_id,
                filename=filename,
                total_size=total_size,
                metadata=metadata or {}
            )
            self._callbacks[progress_id] = []
            return progress_id
    
    async def start_progress(self, progress_id: str) -> None:
        """
        Mark progress as started.
        
        Args:
            progress_id: ID of the progress tracker
        """
        async with self._lock:
            if progress_id in self._progress_info:
                progress = self._progress_info[progress_id]
                progress.status = ProgressStatus.IN_PROGRESS
                progress.start_time = time.time()
                await self._notify_callbacks(progress_id, progress)
    
    async def update_progress(self, progress_id: str, processed_size: int) -> None:
        """
        Update progress with processed size.
        
        Args:
            progress_id: ID of the progress tracker
            processed_size: Number of bytes processed so far
        """
        async with self._lock:
            if progress_id in self._progress_info:
                progress = self._progress_info[progress_id]
                progress.processed_size = min(processed_size, progress.total_size)
                
                # Auto-complete if all bytes processed
                if progress.processed_size >= progress.total_size:
                    progress.status = ProgressStatus.COMPLETED
                    progress.end_time = time.time()
                
                await self._notify_callbacks(progress_id, progress)
    
    async def complete_progress(self, progress_id: str) -> None:
        """
        Mark progress as completed.
        
        Args:
            progress_id: ID of the progress tracker
        """
        async with self._lock:
            if progress_id in self._progress_info:
                progress = self._progress_info[progress_id]
                progress.status = ProgressStatus.COMPLETED
                progress.end_time = time.time()
                progress.processed_size = progress.total_size
                await self._notify_callbacks(progress_id, progress)
    
    async def fail_progress(self, progress_id: str, error_message: str) -> None:
        """
        Mark progress as failed.
        
        Args:
            progress_id: ID of the progress tracker
            error_message: Error message describing the failure
        """
        async with self._lock:
            if progress_id in self._progress_info:
                progress = self._progress_info[progress_id]
                progress.status = ProgressStatus.FAILED
                progress.end_time = time.time()
                progress.error_message = error_message
                await self._notify_callbacks(progress_id, progress)
    
    async def cancel_progress(self, progress_id: str) -> None:
        """
        Mark progress as cancelled.
        
        Args:
            progress_id: ID of the progress tracker
        """
        async with self._lock:
            if progress_id in self._progress_info:
                progress = self._progress_info[progress_id]
                progress.status = ProgressStatus.CANCELLED
                progress.end_time = time.time()
                await self._notify_callbacks(progress_id, progress)
    
    async def get_progress(self, progress_id: str) -> Optional[ProgressInfo]:
        """
        Get progress information.
        
        Args:
            progress_id: ID of the progress tracker
            
        Returns:
            ProgressInfo if found, None otherwise
        """
        async with self._lock:
            return self._progress_info.get(progress_id)
    
    async def get_all_progress(self) -> Dict[str, ProgressInfo]:
        """
        Get all progress information.
        
        Returns:
            Dictionary mapping progress IDs to ProgressInfo
        """
        async with self._lock:
            return self._progress_info.copy()
    
    async def cleanup_completed(self, max_age_seconds: int = 3600) -> None:
        """
        Clean up completed progress entries older than max_age_seconds.
        
        Args:
            max_age_seconds: Maximum age in seconds for completed entries
        """
        current_time = time.time()
        async with self._lock:
            to_remove = []
            for progress_id, progress in self._progress_info.items():
                if (progress.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED] and
                    progress.end_time is not None and
                    current_time - progress.end_time > max_age_seconds):
                    to_remove.append(progress_id)
            
            for progress_id in to_remove:
                del self._progress_info[progress_id]
                if progress_id in self._callbacks:
                    del self._callbacks[progress_id]
    
    async def add_callback(self, progress_id: str, 
                          callback: Callable[[ProgressInfo], None]) -> None:
        """
        Add a callback to be notified of progress updates.
        
        Args:
            progress_id: ID of the progress tracker
            callback: Callback function to be called on updates
        """
        async with self._lock:
            if progress_id in self._callbacks:
                self._callbacks[progress_id].append(callback)
    
    async def remove_callback(self, progress_id: str, 
                            callback: Callable[[ProgressInfo], None]) -> None:
        """
        Remove a callback from progress updates.
        
        Args:
            progress_id: ID of the progress tracker
            callback: Callback function to remove
        """
        async with self._lock:
            if progress_id in self._callbacks:
                try:
                    self._callbacks[progress_id].remove(callback)
                except ValueError:
                    pass  # Callback not found
    
    async def _notify_callbacks(self, progress_id: str, progress: ProgressInfo) -> None:
        """
        Notify all callbacks for a progress update.
        
        Args:
            progress_id: ID of the progress tracker
            progress: Updated progress information
        """
        if progress_id in self._callbacks:
            for callback in self._callbacks[progress_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(progress)
                    else:
                        callback(progress)
                except Exception:
                    # Ignore callback errors to prevent disrupting progress tracking
                    pass


class BatchProgressTracker:
    """Tracks progress for batch upload operations."""
    
    def __init__(self):
        """Initialize batch progress tracker."""
        self._batch_progress: Dict[str, Dict[str, Any]] = {}
        self._file_progress: Dict[str, Dict[str, ProgressInfo]] = {}
        self._lock = asyncio.Lock()
    
    async def create_batch(self, batch_id: str, total_files: int) -> None:
        """
        Create a new batch progress tracker.
        
        Args:
            batch_id: ID of the batch
            total_files: Total number of files in the batch
        """
        async with self._lock:
            self._batch_progress[batch_id] = {
                "total_files": total_files,
                "completed_files": 0,
                "failed_files": 0,
                "start_time": time.time(),
                "end_time": None,
                "status": ProgressStatus.IN_PROGRESS
            }
            self._file_progress[batch_id] = {}
    
    async def add_file_to_batch(self, batch_id: str, file_progress_id: str, 
                              progress_info: ProgressInfo) -> None:
        """
        Add a file progress to a batch.
        
        Args:
            batch_id: ID of the batch
            file_progress_id: ID of the file progress
            progress_info: Progress information for the file
        """
        async with self._lock:
            if batch_id in self._file_progress:
                self._file_progress[batch_id][file_progress_id] = progress_info
    
    async def update_batch_progress(self, batch_id: str) -> None:
        """
        Update batch progress based on individual file progress.
        
        Args:
            batch_id: ID of the batch
        """
        async with self._lock:
            if batch_id not in self._batch_progress:
                return
            
            batch_info = self._batch_progress[batch_id]
            file_progresses = self._file_progress.get(batch_id, {})
            
            completed = sum(1 for p in file_progresses.values() 
                          if p.status == ProgressStatus.COMPLETED)
            failed = sum(1 for p in file_progresses.values() 
                        if p.status == ProgressStatus.FAILED)
            
            batch_info["completed_files"] = completed
            batch_info["failed_files"] = failed
            
            total_files = batch_info["total_files"]
            if completed + failed >= total_files:
                batch_info["status"] = ProgressStatus.COMPLETED
                batch_info["end_time"] = time.time()
    
    async def get_batch_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch progress information.
        
        Args:
            batch_id: ID of the batch
            
        Returns:
            Batch progress information if found, None otherwise
        """
        async with self._lock:
            batch_info = self._batch_progress.get(batch_id)
            if batch_info is None:
                return None
            
            # Calculate overall progress percentage
            total_files = batch_info["total_files"]
            completed_files = batch_info["completed_files"]
            failed_files = batch_info["failed_files"]
            
            if total_files == 0:
                progress_percentage = 100.0
            else:
                progress_percentage = ((completed_files + failed_files) / total_files) * 100.0
            
            return {
                **batch_info,
                "progress_percentage": progress_percentage,
                "in_progress_files": total_files - completed_files - failed_files
            }
    
    async def get_batch_file_progress(self, batch_id: str) -> Dict[str, ProgressInfo]:
        """
        Get progress information for all files in a batch.
        
        Args:
            batch_id: ID of the batch
            
        Returns:
            Dictionary mapping file progress IDs to ProgressInfo
        """
        async with self._lock:
            return self._file_progress.get(batch_id, {}).copy()