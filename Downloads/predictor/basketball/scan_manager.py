"""
Background Scan Manager for Crown Picks
Handles long-running scans that persist even when browser is closed
"""

import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class ScanManager:
    """Manages background scan tasks."""
    
    def __init__(self):
        self.scans: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def start_scan(self, scan_type: str, date: str, scan_function, *args, **kwargs) -> str:
        """Start a new background scan.
        
        Args:
            scan_type: 'total' or 'team'
            date: Date for the scan
            scan_function: Function to execute
            *args, **kwargs: Arguments for scan_function
            
        Returns:
            Scan ID
        """
        scan_id = str(uuid.uuid4())
        
        with self.lock:
            self.scans[scan_id] = {
                'id': scan_id,
                'type': scan_type,
                'date': date,
                'status': 'running',
                'progress': 0,
                'total': 0,
                'current_game': None,
                'started_at': datetime.now().isoformat(),
                'finished_at': None,
                'results': None,
                'error': None,
                'logs': []
            }
        
        # Start background thread
        thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id, scan_function, args, kwargs),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started background scan {scan_id} ({scan_type}) for {date}")
        return scan_id
    
    def _run_scan(self, scan_id: str, scan_function, args, kwargs):
        """Execute scan in background thread."""
        try:
            # Create callback to update progress
            def progress_callback(current, total, game_info=None, log_msg=None):
                with self.lock:
                    if scan_id in self.scans:
                        self.scans[scan_id]['progress'] = current
                        self.scans[scan_id]['total'] = total
                        if game_info:
                            self.scans[scan_id]['current_game'] = game_info
                        if log_msg:
                            self.scans[scan_id]['logs'].append({
                                'time': datetime.now().isoformat(),
                                'message': log_msg
                            })
            
            # Run the scan function
            results = scan_function(*args, progress_callback=progress_callback, **kwargs)
            
            # Mark as completed
            with self.lock:
                if scan_id in self.scans:
                    self.scans[scan_id]['status'] = 'completed'
                    self.scans[scan_id]['finished_at'] = datetime.now().isoformat()
                    self.scans[scan_id]['results'] = results
                    self.scans[scan_id]['logs'].append({
                        'time': datetime.now().isoformat(),
                        'message': '✅ Scan completed successfully'
                    })
            
            logger.info(f"Scan {scan_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Scan {scan_id} failed: {e}", exc_info=True)
            with self.lock:
                if scan_id in self.scans:
                    self.scans[scan_id]['status'] = 'failed'
                    self.scans[scan_id]['finished_at'] = datetime.now().isoformat()
                    self.scans[scan_id]['error'] = str(e)
                    self.scans[scan_id]['logs'].append({
                        'time': datetime.now().isoformat(),
                        'message': f'❌ Scan failed: {e}'
                    })
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """Get status of a scan."""
        with self.lock:
            return self.scans.get(scan_id)
    
    def get_all_scans(self) -> List[Dict]:
        """Get all scans."""
        with self.lock:
            return list(self.scans.values())
    
    def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan."""
        with self.lock:
            if scan_id in self.scans:
                del self.scans[scan_id]
                return True
            return False
    
    def cleanup_old_scans(self, max_age_hours: int = 24):
        """Remove scans older than max_age_hours."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.lock:
            to_delete = []
            for scan_id, scan in self.scans.items():
                started = datetime.fromisoformat(scan['started_at']).timestamp()
                if started < cutoff:
                    to_delete.append(scan_id)
            
            for scan_id in to_delete:
                del self.scans[scan_id]
            
            if to_delete:
                logger.info(f"Cleaned up {len(to_delete)} old scans")


# Global scan manager instance
scan_manager = ScanManager()
