import pytest
import multiprocessing as mp
from unittest.mock import patch, MagicMock
from stock_monitoring_app.utils.process_manager import launch_ticker_monitor_process, canonical_monitor_worker

class TestProcessManager:
    
    @patch('stock_monitoring_app.utils.process_manager.mp.Process')
    @patch('stock_monitoring_app.utils.process_manager.mp.Pipe')
    def test_launch_ticker_monitor_process(self, mock_pipe, mock_process):
        """Test launching a ticker monitor process"""
        # Configure mocks
        mock_parent_conn = MagicMock()
        mock_child_conn = MagicMock()
        mock_pipe.return_value = (mock_parent_conn, mock_child_conn)
        
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        
        # Call the function
        process, conn = launch_ticker_monitor_process(
            ticker="AAPL",
            entry_price=0,
            scope="intraday",
            leverage=1,
            stop_loss=0.05
        )
        
        # Verify process was created and started
        mock_process.assert_called_once()
        mock_process_instance.start.assert_called_once()
        
        # Verify the returned values
        assert process == mock_process_instance
        assert conn == mock_parent_conn
    
    @patch('stock_monitoring_app.utils.process_manager.mp.Process')
    @patch('stock_monitoring_app.utils.process_manager.mp.Pipe')
    def test_launch_ticker_monitor_process_error(self, mock_pipe, mock_process):
        """Test error handling when launching a process fails"""
        # Configure mock to raise an exception
        mock_process.side_effect = Exception("Test error")
        
        # Call the function
        process, conn = launch_ticker_monitor_process(
            ticker="AAPL",
            entry_price=0,
            scope="intraday"
        )
        
        # Verify the returned values on error
        assert process is None
        assert conn is None
    
    @patch('stock_monitoring_app.utils.process_manager.TickerMonitor')
    def test_canonical_monitor_worker(self, mock_ticker_monitor):
        """Test the worker function that runs in the child process"""
        # Configure mocks
        mock_conn = MagicMock()
        mock_monitor_instance = MagicMock()
        mock_ticker_monitor.return_value = mock_monitor_instance
        
        # Call the function in a separate process to avoid affecting the main test process
        p = mp.Process(
            target=canonical_monitor_worker,
            args=("AAPL", 0, "intraday", 1, 0.05, mock_conn)
        )
        p.start()
        p.join(timeout=1)  # Wait for 1 second max
        
        # We can't easily assert on what happened in the other process,
        # but we can verify the process completed
        assert not p.is_alive()
        
    def test_pipe_as_queue(self):
        """Test the PipeAsQueue adapter"""
        from stock_monitoring_app.utils.process_manager import PipeAsQueue
        
        # Create a mock connection
        mock_conn = MagicMock()
        
        # Create a PipeAsQueue instance
        queue = PipeAsQueue(mock_conn)
        
        # Put an item in the queue
        test_item = {"type": "test", "data": "test_data"}
        queue.put(test_item)
        
        # Verify the item was sent through the connection
        mock_conn.send.assert_called_once_with(test_item)
        
    def test_writer_to_pipe(self):
        """Test the WriterToPipe class"""
        from stock_monitoring_app.utils.process_manager import WriterToPipe
        
        # Create a mock connection
        mock_conn = MagicMock()
        
        # Create a WriterToPipe instance
        writer = WriterToPipe(mock_conn, origin="test_origin")
        
        # Write something
        writer.write("test message")
        
        # Verify the message was sent through the connection
        mock_conn.send.assert_called_once()
        args, _ = mock_conn.send.call_args
        assert args[0]["type"] == "test_origin"
        assert args[0]["data"] == "test message"
        assert "pid" in args[0]
