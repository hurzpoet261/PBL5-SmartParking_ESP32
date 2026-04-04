"""
Unit tests for hardware abstraction layer
Tests RFIDReader class functionality
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from machine import Pin


class TestRFIDReader(unittest.TestCase):
    """Test cases for RFIDReader class"""
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_init_creates_spi_and_reader(self, mock_mfrc522, mock_spi):
        """Test that RFIDReader initializes SPI bus and MFRC522 reader"""
        from firmware.refactored.hardware import RFIDReader
        
        # Create mock pins
        sck = Mock(spec=Pin)
        mosi = Mock(spec=Pin)
        miso = Mock(spec=Pin)
        cs = Mock(spec=Pin)
        rst = Mock(spec=Pin)
        
        # Initialize reader
        reader = RFIDReader(
            spi_bus=1,
            sck=sck,
            mosi=mosi,
            miso=miso,
            cs=cs,
            rst=rst
        )
        
        # Verify SPI was initialized with correct parameters
        mock_spi.assert_called_once_with(
            1,
            baudrate=1_000_000,
            polarity=0,
            phase=0,
            sck=sck,
            mosi=mosi,
            miso=miso
        )
        
        # Verify MFRC522 was initialized
        mock_mfrc522.assert_called_once()
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_get_version_returns_chip_version(self, mock_mfrc522, mock_spi):
        """Test that get_version returns the chip version"""
        from firmware.refactored.hardware import RFIDReader
        
        # Setup mock
        mock_reader_instance = Mock()
        mock_reader_instance.version.return_value = 0x92
        mock_mfrc522.return_value = mock_reader_instance
        
        # Create reader
        reader = RFIDReader(1, Mock(), Mock(), Mock(), Mock(), Mock())
        
        # Test get_version
        version = reader.get_version()
        
        assert version == 0x92
        mock_reader_instance.version.assert_called_once()
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_scan_returns_formatted_uid(self, mock_mfrc522, mock_spi):
        """Test that scan returns properly formatted UID with 0x prefix"""
        from firmware.refactored.hardware import RFIDReader
        
        # Setup mock
        mock_reader_instance = Mock()
        mock_reader_instance.OK = 0
        mock_reader_instance.REQIDL = 0x26
        mock_reader_instance.request.return_value = (0, None)
        mock_reader_instance.anticoll.return_value = (0, [0xa3, 0xd6, 0xce, 0x05])
        mock_mfrc522.return_value = mock_reader_instance
        
        # Create reader
        reader = RFIDReader(1, Mock(), Mock(), Mock(), Mock(), Mock())
        
        # Test scan
        uid = reader.scan()
        
        assert uid == "0xa3d6ce05"
        mock_reader_instance.request.assert_called_once_with(0x26)
        mock_reader_instance.anticoll.assert_called_once()
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_scan_returns_none_on_no_card(self, mock_mfrc522, mock_spi):
        """Test that scan returns None when no card is detected"""
        from firmware.refactored.hardware import RFIDReader
        
        # Setup mock - request fails
        mock_reader_instance = Mock()
        mock_reader_instance.OK = 0
        mock_reader_instance.REQIDL = 0x26
        mock_reader_instance.request.return_value = (1, None)  # Non-OK status
        mock_mfrc522.return_value = mock_reader_instance
        
        # Create reader
        reader = RFIDReader(1, Mock(), Mock(), Mock(), Mock(), Mock())
        
        # Test scan
        uid = reader.scan()
        
        assert uid is None
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_scan_returns_none_on_anticoll_error(self, mock_mfrc522, mock_spi):
        """Test that scan returns None when anticoll fails"""
        from firmware.refactored.hardware import RFIDReader
        
        # Setup mock - anticoll fails
        mock_reader_instance = Mock()
        mock_reader_instance.OK = 0
        mock_reader_instance.REQIDL = 0x26
        mock_reader_instance.request.return_value = (0, None)
        mock_reader_instance.anticoll.return_value = (1, None)  # Non-OK status
        mock_mfrc522.return_value = mock_reader_instance
        
        # Create reader
        reader = RFIDReader(1, Mock(), Mock(), Mock(), Mock(), Mock())
        
        # Test scan
        uid = reader.scan()
        
        assert uid is None
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_scan_handles_exception_gracefully(self, mock_mfrc522, mock_spi):
        """Test that scan returns None on exception"""
        from firmware.refactored.hardware import RFIDReader
        
        # Setup mock to raise exception
        mock_reader_instance = Mock()
        mock_reader_instance.request.side_effect = Exception("Hardware error")
        mock_mfrc522.return_value = mock_reader_instance
        
        # Create reader
        reader = RFIDReader(1, Mock(), Mock(), Mock(), Mock(), Mock())
        
        # Test scan - should not raise exception
        uid = reader.scan()
        
        assert uid is None
    
    @patch('firmware.refactored.hardware.SPI')
    @patch('firmware.refactored.hardware.MFRC522')
    def test_halt_calls_reader_halt(self, mock_mfrc522, mock_spi):
        """Test that halt calls the underlying reader's halt method"""
        from firmware.refactored.hardware import RFIDReader
        
        # Setup mock
        mock_reader_instance = Mock()
        mock_mfrc522.return_value = mock_reader_instance
        
        # Create reader
        reader = RFIDReader(1, Mock(), Mock(), Mock(), Mock(), Mock())
        
        # Test halt
        reader.halt()
        
        mock_reader_instance.halt.assert_called_once()


if __name__ == '__main__':
    unittest.main()
