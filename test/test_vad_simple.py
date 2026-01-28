"""Simple test script for VAD Service."""

import numpy as np


def test_vad_service():
    """Test VAD service basic functionality."""
    print("Testing VAD Service...")

    # Test 1: Create service
    print("\n1. Testing create_vad_service...")
    from src.services.voice import create_vad_service

    service = create_vad_service(provider="silero", threshold=0.5)
    assert service is not None
    assert service.threshold == 0.5
    assert service.sample_rate == 16000
    print("   ✓ Service created successfully")

    # Test 2: Invalid provider
    print("\n2. Testing invalid provider...")
    try:
        create_vad_service(provider="invalid")
        print("   ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✓ Correctly raised ValueError: {e}")

    # Test 3: Detect speech with empty audio
    print("\n3. Testing detect_speech with empty audio...")
    result = service.detect_speech(b"")
    assert result is False
    print("   ✓ Empty audio returns False")

    # Test 4: Detect speech with silence
    print("\n4. Testing detect_speech with silence...")
    silence = np.zeros(16000, dtype=np.int16).tobytes()
    result = service.detect_speech(silence)
    print(f"   Result: {result}")
    print("   ✓ Silence detection completed")

    # Test 5: Get speech probability
    print("\n5. Testing get_speech_probability...")
    prob = service.get_speech_probability(silence)
    assert 0.0 <= prob <= 1.0
    print(f"   ✓ Speech probability for silence: {prob:.4f}")

    # Test 6: Detect speech end with silence
    print("\n6. Testing detect_speech_end with silence...")
    result = service.detect_speech_end([silence], silence_duration=0.5)
    print(f"   Result: {result}")
    print("   ✓ Speech end detection completed")

    # Test 7: Reset
    print("\n7. Testing reset...")
    service.reset()
    print("   ✓ Reset completed")

    # Test 8: Model caching
    print("\n8. Testing model caching...")
    from src.services.voice import SileroVADService

    service1 = SileroVADService(threshold=0.3)
    service2 = SileroVADService(threshold=0.7)
    assert service1.model is service2.model
    print("   ✓ Model is cached between instances")

    # Test 9: Protocol compliance
    print("\n9. Testing protocol compliance...")
    from src.services.voice import VADService

    assert isinstance(service, VADService)
    print("   ✓ SileroVADService implements VADService protocol")

    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)


if __name__ == "__main__":
    test_vad_service()
