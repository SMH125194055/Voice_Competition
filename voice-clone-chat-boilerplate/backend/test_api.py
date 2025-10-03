"""
Simple test script for the Voice Chat API endpoints.
Run the server first with: uvicorn main:app --reload --port 8000
"""

import requests
import json
import base64

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the root endpoint."""
    print("\n1. Testing health check...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_chat():
    """Test the chat endpoint."""
    print("\n2. Testing chat endpoint...")
    data = {"message": "Hello! What is the name of president of Pakistan?"}
    response = requests.post(f"{BASE_URL}/chat", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200


def test_transcribe():
    """Test the transcribe endpoint."""
    print("\n3. Testing transcribe endpoint...")
    audio_file = "audio/test-english.wav"
    
    try:
        with open(audio_file, "rb") as f:
            files = {"audio": f}
            response = requests.post(f"{BASE_URL}/transcribe", files=files)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
            return response.status_code == 200
    except FileNotFoundError:
        print(f"Audio file not found: {audio_file}")
        print("Skipping this test.")
        return False


def test_speak():
    """Test the speak endpoint."""
    print("\n4. Testing speak endpoint...")
    data = {"text": "Hello, this is a test of the text to speech system."}
    response = requests.post(f"{BASE_URL}/speak", json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        output_file = "test_output.wav"
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Audio saved to: {output_file}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_chat_voice():
    """Test the full voice chat pipeline."""
    print("\n5. Testing chat-voice endpoint (full pipeline)...")
    audio_file = "audio/test-english.wav"
    
    try:
        with open(audio_file, "rb") as f:
            files = {"audio": f}
            response = requests.post(f"{BASE_URL}/chat-voice", files=files)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Get text from header
                reply_text_encoded = response.headers.get("X-Reply-Text", "")
                encoding = response.headers.get("X-Reply-Text-Encoding", "plain")
                
                # Decode if base64
                if encoding == "base64" and reply_text_encoded:
                    reply_text = base64.b64decode(reply_text_encoded).decode('utf-8')
                else:
                    reply_text = reply_text_encoded
                
                print(f"Reply text: {reply_text}")
                
                # Save audio
                output_file = "test_chat_voice_output.wav"
                with open(output_file, "wb") as out:
                    out.write(response.content)
                print(f"Reply audio saved to: {output_file}")
                return True
            else:
                print(f"Error: {response.text}")
                return False
    except FileNotFoundError:
        print(f"Audio file not found: {audio_file}")
        print("Skipping this test.")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Voice Chat API Test Suite")
    print("=" * 60)
    print("\nMake sure the server is running:")
    print("  uvicorn main:app --reload --port 8000")
    print("=" * 60)
    
    results = {
        "Health Check": test_health_check(),
        "Chat": test_chat(),
        "Transcribe": test_transcribe(),
        "Speak": test_speak(),
        "Chat Voice": test_chat_voice(),
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED/SKIPPED"
        print(f"{test_name}: {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()


